"""Backtest: how often the expanding P10–P90 band contains the actual."""

from dataclasses import dataclass
from datetime import date, timedelta

from backend.app.services.band import actual_band, percentiles_before
from backend.app.services.decision import DecisionHour

# One row: delivery day, actual MW, band_low, band_high.
BandHour = tuple[date, float, float, float]


@dataclass(frozen=True)
class Coverage:
    days: int
    hours: int
    inside: int
    coverage_pct: float | None


def band_coverage(rows: list[BandHour]) -> Coverage:
    """Count hours where band_low <= actual <= band_high.

    `rows` must already be hours that have both an actual and a band
    (delivery days with at least three prior days).
    """
    if not rows:
        return Coverage(days=0, hours=0, inside=0, coverage_pct=None)
    days = {day for day, _actual, _low, _high in rows}
    hours = len(rows)
    inside = sum(1 for _day, actual, low, high in rows if low <= actual <= high)
    return Coverage(
        days=len(days),
        hours=hours,
        inside=inside,
        coverage_pct=100.0 * inside / hours,
    )


def expanding_band_hours(
    chosen: list[tuple[DecisionHour, float | None]],
    start: date,
    end: date,
) -> list[BandHour]:
    """Hours in [start, end] that have an expanding-window band and an actual.

    Percentiles use delivery days strictly before each day D, including days
    before `start` when they are present in `chosen`.
    """
    errors_by_day: dict[date, list[float]] = {}
    by_day: dict[date, list[tuple[DecisionHour, float | None]]] = {}
    for hour, actual in chosen:
        day = hour.start_time.date()
        by_day.setdefault(day, []).append((hour, actual))
        if actual is not None:
            errors_by_day.setdefault(day, []).append(hour.generation - actual)

    rows: list[BandHour] = []
    cursor = start
    while cursor <= end:
        error_p10, error_p90, _history_days = percentiles_before(errors_by_day, cursor)
        if error_p10 is not None and error_p90 is not None:
            for hour, actual in by_day.get(cursor, []):
                if actual is None:
                    continue
                low, high = actual_band(hour.generation, error_p10, error_p90)
                rows.append((cursor, actual, low, high))
        cursor += timedelta(days=1)
    return rows
