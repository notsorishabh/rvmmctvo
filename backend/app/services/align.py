"""Turn half-hourly actuals into the hourly values the forecast uses."""

from datetime import datetime, timedelta


def hourly_actual(actuals: dict[datetime, float], hour_start: datetime) -> float | None:
    """Mean of H:00 and H:30. Missing either half-hour drops the hour."""
    on_the_hour = actuals.get(hour_start)
    half_past = actuals.get(hour_start + timedelta(minutes=30))
    if on_the_hour is None or half_past is None:
        return None
    return (on_the_hour + half_past) / 2.0


def align_hours(
    actuals: dict[datetime, float],
    hours: list[datetime],
) -> list[tuple[datetime, float]]:
    aligned: list[tuple[datetime, float]] = []
    for hour_start in hours:
        value = hourly_actual(actuals, hour_start)
        if value is None:
            continue
        aligned.append((hour_start, value))
    return aligned
