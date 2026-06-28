"""Configuration loaded from the project .env file.

All GBQ project/dataset identifiers and cost guardrails live here so the
notebook and SQL helpers share a single source of truth.
"""
from pathlib import Path
from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = PROJECT_ROOT / "sql"
SCHEMA_DIR = PROJECT_ROOT / "dimensions_gbq_schema"
INPUT_DIR = PROJECT_ROOT / "input-data"

load_dotenv(PROJECT_ROOT / ".env")

BILLING_PROJECT = os.getenv("BILLING_PROJECT", "").strip()
DIMENSIONS_DATASET = os.getenv("DIMENSIONS_DATASET", "dimensions-ai.data_analytics").strip()
ALTMETRIC_DATASET = os.getenv("ALTMETRIC_DATASET", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

MAX_QUERY_GIB = float(os.getenv("MAX_QUERY_GIB", "5.0"))
BQ_PRICE_PER_TIB = float(os.getenv("BQ_PRICE_PER_TIB", "6.25"))

OUTPUT_DIR = PROJECT_ROOT / os.getenv("OUTPUT_DIR", "output-data")
OUTPUT_DIR.mkdir(exist_ok=True)


def require(name: str) -> str:
    """Return a required config value or fail fast naming the missing key."""
    value = globals().get(name, "")
    if not value:
        raise ValueError(
            f"{name} is empty. Set it in {PROJECT_ROOT / '.env'} before running this step."
        )
    return value
