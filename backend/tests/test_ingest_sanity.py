"""The built database must satisfy the section 6 load checks."""

from backend.app.config import DB_PATH, EXPECTED_ACTUALS
from backend.scripts.ingest import assert_database


def test_ingested_database_meets_spec():
    assert DB_PATH.is_file(), "backend/data/wind.db is missing; run backend/scripts/ingest.py"
    summary = assert_database(DB_PATH)
    assert summary["actuals"] == EXPECTED_ACTUALS
    assert summary["runs"] > 0
    assert summary["forecast_rows"] > 0
    assert "2025-12-31" in summary["runs_per_day"]
    assert "2026-01-31" in summary["runs_per_day"]
