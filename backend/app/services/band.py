"""Turn historical forecast error into a band around the actual.

error = forecast - actual, so actual = forecast - error.
The P10–P90 band of the actual is therefore

    forecast - P90(error)  ..  forecast - P10(error)

and the lower edge cannot go below 0 MW.
"""

from datetime import date

from backend.app.services.metrics import linear_percentile

MIN_HISTORY_DAYS = 3


def actual_band(forecast: float, error_p10: float, error_p90: float) -> tuple[float, float]:
    """Likely range of the actual, in MW. `band_low` is clamped at 0."""
    low = forecast - error_p90
    high = forecast - error_p10
    low = max(0.0, low)
    if high < low:
        high = low
    return low, high


def _mw(value: float) -> str:
    return f"{round(value):,}"


def planning_sentence(error_p10: float, error_p90: float) -> str:
    """Describe where the actual has landed, without pretending the band is symmetric."""
    if error_p10 > 0 and error_p90 > 0:
        middle = f"between {_mw(error_p10)} and {_mw(error_p90)} MW below the forecast"
    elif error_p10 < 0 and error_p90 < 0:
        middle = f"between {_mw(-error_p90)} and {_mw(-error_p10)} MW above the forecast"
    else:
        below = max(error_p90, 0.0)
        above = max(-error_p10, 0.0)
        middle = f"between {_mw(below)} MW below and {_mw(above)} MW above the forecast"
    return (
        "At this cutoff, actual wind has typically landed "
        f"{middle} (80% of hours)."
    )


def percentiles_before(
    errors_by_day: dict[date, list[float]],
    delivery_day: date,
) -> tuple[float | None, float | None, int]:
    """P10 and P90 of errors on delivery days strictly before `delivery_day`.

    Returns (None, None, n) when fewer than three prior days have an error.
    """
    prior_days = sorted(day for day, errors in errors_by_day.items() if day < delivery_day and errors)
    errors = [error for day in prior_days for error in errors_by_day[day]]
    history_days = len(prior_days)
    if history_days < MIN_HISTORY_DAYS or not errors:
        return None, None, history_days
    return linear_percentile(errors, 0.10), linear_percentile(errors, 0.90), history_days
