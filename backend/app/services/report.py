"""Load rows and apply the pure forecast, alignment, and metric functions."""

from datetime import date, datetime, time, timedelta

from backend.app import db
from backend.app.config import DELIVERY_END, DELIVERY_START
from backend.app.services.align import hourly_actual
from backend.app.services.decision import (
    DecisionHour,
    ForecastPoint,
    cutoff_timestamp,
    select_decision_forecast,
)
from backend.app.services.metrics import Summary, error_by_horizon, error_by_hour, summarise
from backend.app.times import UTC, day_bounds, format_utc, parse_utc


def _each_day(start: date, end: date):
    cursor = start
    while cursor <= end:
        yield cursor
        cursor += timedelta(days=1)


def _window(start: date, end: date) -> tuple[str, str]:
    opened = format_utc(datetime.combine(start, time(0), tzinfo=UTC))
    closed = format_utc(datetime.combine(end + timedelta(days=1), time(0), tzinfo=UTC))
    return opened, closed


def _read(sql: str, params: tuple) -> list[dict]:
    connection = db.connect_readonly()
    try:
        return db.fetch_all(connection, sql, params)
    finally:
        connection.close()


def load_window(start: date, end: date) -> tuple[dict[datetime, float], list[ForecastPoint]]:
    opened, closed = _window(start, end)
    actual_rows = _read(
        """
        SELECT start_time, generation
        FROM actuals
        WHERE start_time >= ? AND start_time < ?
        ORDER BY start_time
        """,
        (opened, closed),
    )
    forecast_rows = _read(
        """
        SELECT publish_time, start_time, generation, horizon_h
        FROM forecasts
        WHERE start_time >= ? AND start_time < ?
        ORDER BY publish_time, start_time
        """,
        (opened, closed),
    )
    actuals = {parse_utc(row["start_time"]): float(row["generation"]) for row in actual_rows}
    forecasts = [
        ForecastPoint(
            publish_time=parse_utc(row["publish_time"]),
            start_time=parse_utc(row["start_time"]),
            generation=float(row["generation"]),
            horizon_h=float(row["horizon_h"]),
        )
        for row in forecast_rows
    ]
    return actuals, forecasts


def decision_hours(
    actuals: dict[datetime, float],
    forecasts: list[ForecastPoint],
    start: date,
    end: date,
    cutoff: time,
) -> list[tuple[DecisionHour, float | None]]:
    chosen: list[tuple[DecisionHour, float | None]] = []
    for day in _each_day(start, end):
        for hour in select_decision_forecast(forecasts, day, cutoff):
            chosen.append((hour, hourly_actual(actuals, hour.start_time)))
    return chosen


def aligned_pairs(
    chosen: list[tuple[DecisionHour, float | None]],
) -> list[tuple[float, float, int]]:
    return [
        (hour.generation, actual, hour.start_time.hour)
        for hour, actual in chosen
        if actual is not None
    ]


def summary_for(chosen: list[tuple[DecisionHour, float | None]]) -> Summary:
    return summarise([(forecast, actual) for forecast, actual, _hour in aligned_pairs(chosen)])


def hour_breakdown(chosen: list[tuple[DecisionHour, float | None]]):
    return error_by_hour(aligned_pairs(chosen))


def horizon_breakdown(actuals: dict[datetime, float], forecasts: list[ForecastPoint]):
    rows: list[tuple[float, float, float]] = []
    for point in forecasts:
        actual = hourly_actual(actuals, point.start_time)
        if actual is None:
            continue
        rows.append((point.generation, actual, point.horizon_h))
    return error_by_horizon(rows)


def runs_per_day() -> list[dict]:
    rows = _read("SELECT DISTINCT publish_time FROM forecasts ORDER BY publish_time", ())
    grouped: dict[str, list[str]] = {}
    for row in rows:
        published = row["publish_time"]
        grouped.setdefault(published[:10], []).append(published)
    return [
        {"date": day, "count": len(times), "publish_times": times}
        for day, times in grouped.items()
    ]


def full_range() -> tuple[date, date]:
    return date.fromisoformat(DELIVERY_START), date.fromisoformat(DELIVERY_END)


def day_actuals(actuals: dict[datetime, float], delivery_day: date) -> list[tuple[datetime, float]]:
    start, end = day_bounds(delivery_day)
    hours: list[tuple[datetime, float]] = []
    cursor = start
    while cursor < end:
        value = hourly_actual(actuals, cursor)
        if value is not None:
            hours.append((cursor, value))
        cursor += timedelta(hours=1)
    return hours


def revisions_for(
    actuals: dict[datetime, float],
    forecasts: list[ForecastPoint],
    delivery_day: date,
) -> dict[datetime, list[ForecastPoint]]:
    start, end = day_bounds(delivery_day)
    grouped: dict[datetime, list[ForecastPoint]] = {}
    for point in forecasts:
        if start <= point.start_time < end:
            grouped.setdefault(point.publish_time, []).append(point)
    for points in grouped.values():
        points.sort(key=lambda item: item.start_time)
    return dict(sorted(grouped.items()))
