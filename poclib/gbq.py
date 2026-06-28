"""BigQuery client and the dry-run cost guard.

Every live query goes through `run_guarded`, which dry-runs first, prints the
estimated bytes scanned and dollar cost, and refuses to execute anything above
the configured size threshold unless explicitly confirmed. This is the single
chokepoint that enforces "dry-run before any live hit to GBQ".
"""
from google.cloud import bigquery
import pandas as pd
import re

from . import config

BYTES_PER_GIB = 2 ** 30
BYTES_PER_TIB = 2 ** 40

_client: bigquery.Client | None = None


def get_client() -> bigquery.Client:
    """Return a cached BigQuery client billed to BILLING_PROJECT (uses ADC)."""
    global _client
    if _client is None:
        _client = bigquery.Client(project=config.require("BILLING_PROJECT"))
    return _client


def estimate_query(sql: str, client: bigquery.Client | None = None) -> dict:
    """Dry-run a query and return its scan-size estimate without executing it.

    NOTE: the Dimensions/Altmetric data are Analytics Hub *linked* datasets, for
    which BigQuery returns `total_bytes_processed = None` on a dry run. In that
    case `bytes` is None and the real guardrail is the `maximum_bytes_billed`
    cap applied in `run_guarded`, which fails the query before billing.
    """
    client = client or get_client()
    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),
    )
    total_bytes = job.total_bytes_processed
    if total_bytes is None:
        return {"bytes": None, "gib": None, "est_usd": None}
    return {
        "bytes": total_bytes,
        "gib": total_bytes / BYTES_PER_GIB,
        "est_usd": total_bytes / BYTES_PER_TIB * config.BQ_PRICE_PER_TIB,
    }


def _format_estimate(estimate: dict) -> str:
    if estimate["bytes"] is None:
        return "scan size not reported by dry-run (Analytics Hub linked dataset)"
    return (
        f"{estimate['gib']:.3f} GiB scanned "
        f"(~${estimate['est_usd']:.4f} at ${config.BQ_PRICE_PER_TIB}/TiB)"
    )


def run_guarded(
    sql: str,
    max_gib: float | None = None,
    confirm: bool = False,
    client: bigquery.Client | None = None,
) -> pd.DataFrame:
    """Execute a query under a hard bytes-billed cap, after a dry-run estimate.

    The cap (`maximum_bytes_billed = max_gib`) makes BigQuery *abort before
    billing* if the query would scan more than the threshold, which protects us
    even when the dry run cannot estimate bytes (the linked-dataset case). When
    the dry run does report an estimate above the limit, we refuse up front.
    Pass `confirm=True` to lift the cap and accept the cost.
    """
    client = client or get_client()
    max_gib = config.MAX_QUERY_GIB if max_gib is None else max_gib

    estimate = estimate_query(sql, client)
    print(f"[dry-run] {_format_estimate(estimate)}")

    if estimate["gib"] is not None and estimate["gib"] > max_gib and not confirm:
        raise RuntimeError(
            f"Query would scan {estimate['gib']:.3f} GiB > limit {max_gib} GiB. "
            f"Re-run with confirm=True to override."
        )

    cap_bytes = None if confirm else int(max_gib * BYTES_PER_GIB)
    job_config = bigquery.QueryJobConfig(maximum_bytes_billed=cap_bytes)
    try:
        job = client.query(sql, job_config=job_config)
        frame = job.result().to_dataframe()
    except Exception as exc:
        if "maximum_bytes_billed" in str(exc) or "bytes billed" in str(exc).lower():
            # BigQuery reports the true scan size as "<N> or higher required",
            # which is our only accurate cost signal for linked datasets.
            required = re.search(r"(\d+)\s+or higher required", str(exc))
            detail = ""
            if required:
                detail = f" Query needs {int(required.group(1)) / BYTES_PER_GIB:.1f} GiB."
            raise RuntimeError(
                f"Query exceeded the {max_gib} GiB bytes-billed cap and was aborted "
                f"before billing.{detail} Narrow the query or re-run with a higher "
                f"max_gib / confirm=True."
            ) from exc
        raise
    billed = job.total_bytes_billed
    if billed is not None:
        print(
            f"[billed] {billed / BYTES_PER_GIB:.3f} GiB "
            f"(${billed / BYTES_PER_TIB * config.BQ_PRICE_PER_TIB:.4f})"
        )
    return frame


def load_sql(name: str, **params) -> str:
    """Load a .sql file from the sql/ directory and substitute {placeholders}.

    Uses double-brace escaping in the .sql file for any literal braces.
    """
    path = config.SQL_DIR / (name if name.endswith(".sql") else f"{name}.sql")
    template = path.read_text()
    return template.format(**params) if params else template


def quote_for_in_clause(values) -> str:
    """Render an iterable of strings as a quoted comma-separated IN(...) body."""
    return ", ".join("'" + str(v).replace("'", "''") + "'" for v in values)
