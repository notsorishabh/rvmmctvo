"""Pick the latest forecast that existed at the buyer's cutoff."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import pandas as pd

from backend.app.times import UTC, day_bounds


@dataclass(frozen=True)
class ForecastPoint:
    publish_time: datetime
    start_time: datetime
    generation: float
    horizon_h: float


@dataclass(frozen=True)
class DecisionHour:
    start_time: datetime
    publish_time: datetime
    generation: float
    horizon_h: float


def cutoff_timestamp(delivery_day: date, cutoff: time) -> datetime:
    """Cutoff is clock time `cutoff` on D-1, in UTC."""
    return datetime.combine(delivery_day - timedelta(days=1), cutoff, tzinfo=UTC)


def select_decision_forecast(
    rows: list[ForecastPoint],
    delivery_day: date,
    cutoff: time,
) -> list[DecisionHour]:
    """Latest publish_time at or before the cutoff, per delivery hour.

    A run published after the cutoff is never used. An empty list means no
    forecast was available at decision time.
    """
    cutoff_ts = cutoff_timestamp(delivery_day, cutoff)
    day_start, day_end = day_bounds(delivery_day)
    candidates = [
        row
        for row in rows
        if row.publish_time <= cutoff_ts and day_start <= row.start_time < day_end
    ]
    if not candidates:
        return []

    frame = pd.DataFrame(
        {
            "publish_time": [row.publish_time for row in candidates],
            "start_time": [row.start_time for row in candidates],
            "generation": [row.generation for row in candidates],
            "horizon_h": [row.horizon_h for row in candidates],
        }
    )
    frame = frame.sort_values(["start_time", "publish_time"], kind="mergesort")
    chosen = frame.groupby("start_time", as_index=False, sort=False).tail(1)
    chosen = chosen.sort_values("start_time", kind="mergesort")

    hours: list[DecisionHour] = []
    for record in chosen.itertuples(index=False):
        hours.append(
            DecisionHour(
                start_time=record.start_time.to_pydatetime(),
                publish_time=record.publish_time.to_pydatetime(),
                generation=float(record.generation),
                horizon_h=float(record.horizon_h),
            )
        )
    return hours
