"""Paths, cutoff, and date bounds. Dates live only in this module."""

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "wind.db"
FRONTEND_DIST = REPO_DIR / "frontend" / "dist"

# The spec lists https://bmrs.elexon.co.uk/api/v1/datasets. That host now
# returns the BMRS website shell. The same dataset paths are served as JSON
# from the Elexon Insights host below.
ELEXON_BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"

FUEL_TYPE = "WIND"
DEFAULT_CUTOFF = "09:00"
CUTOFF_PRESETS: tuple[tuple[str, str], ...] = (
    ("09:00", "09:00"),
    ("09:20", "09:20 EPEX GB"),
    ("09:50", "09:50 N2EX"),
)

DELIVERY_START = "2026-01-02"
DELIVERY_END = "2026-02-01"

ACTUALS_FROM = "2026-01-02"
ACTUALS_TO = "2026-02-01"
EXPECTED_ACTUALS = 1488
ACTUALS_MIN = "2026-01-02T00:00:00Z"
ACTUALS_MAX = "2026-02-01T23:30:00Z"

# Dec 31 is included so the load check can require a run on every day
# from 31 Dec through 31 Jan. The spec's sample window starts 1 Jan;
# the assertion starts 31 Dec.
FORECAST_PUBLISH_FROM = "2025-12-31"
FORECAST_PUBLISH_TO = "2026-01-31"

TIMEZONE_NOTE = (
    "January UK time equals UTC. All times in this app are UTC."
)

ASSUMPTIONS: tuple[str, ...] = (
    "Default decision cutoff is 09:00 UTC on the day before delivery (D-1). "
    "The cutoff is configurable because auctions do not all close at 09:00.",
    "A forecast hour H:00 is compared with the mean of the half-hourly "
    "actuals at H:00 and H:30. If either half-hour is missing, that hour is dropped.",
    "January UK civil time equals UTC, so every timestamp is stored and shown as UTC.",
    "WINDFOR rows with startTime at or before publishTime are not forecasts "
    "and are excluded.",
    "Error is forecast minus actual. A positive error is an over-forecast, "
    "and the actual equals the forecast minus the error.",
    "The shaded band is the likely range of the actual: forecast minus P90 of "
    "the error, up to forecast minus P10 of the error. The lower edge is clamped at 0 MW.",
    "P10 and P90 use delivery days strictly before the selected day, at the same "
    "cutoff. The selected day and later days are excluded. Fewer than 3 prior days "
    "shows no band.",
)
