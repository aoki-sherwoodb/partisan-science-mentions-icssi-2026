"""Helpers for discovering the schema of datasets not documented in this repo.

The Altmetric mention-level dataset (`attention_sources`) is not in the bundled
YAML schemas, so we confirm its table list and nested field paths at runtime via
INFORMATION_SCHEMA before writing the Track-A join.
"""
import pandas as pd

from . import config, gbq


def split_dataset(dataset: str) -> tuple[str, str]:
    """Split a `project.dataset` identifier into (project, dataset)."""
    project, _, dataset_name = dataset.partition(".")
    if not dataset_name:
        raise ValueError(f"Expected 'project.dataset', got '{dataset}'")
    return project, dataset_name


def list_tables(dataset: str, client=None) -> pd.DataFrame:
    """List tables in a `project.dataset` (metadata only, no data scanned)."""
    client = client or gbq.get_client()
    project, dataset_name = split_dataset(dataset)
    rows = [
        {"table": t.table_id, "type": t.table_type}
        for t in client.list_tables(f"{project}.{dataset_name}")
    ]
    return pd.DataFrame(rows)


def describe_table(dataset: str, table: str, max_gib: float | None = None) -> pd.DataFrame:
    """Return every (possibly nested) field path of a table with type + description.

    INFORMATION_SCHEMA queries are tiny, but they still route through the cost
    guard for consistency.
    """
    project, dataset_name = split_dataset(dataset)
    sql = gbq.load_sql(
        "discover_columns",
        project=project,
        dataset=dataset_name,
        table=table,
    )
    return gbq.run_guarded(sql, max_gib=max_gib)


def describe_dimensions_table(table: str) -> pd.DataFrame:
    """Convenience wrapper for the Dimensions dataset."""
    return describe_table(config.DIMENSIONS_DATASET, table)
