"""Hand-computed decision forecast. Do not edit these numbers to match the code."""

from datetime import date, time

from backend.app.services.report import decision_hours, load_window
from backend.app.times import format_utc


def _chosen(delivery: str):
    day = date.fromisoformat(delivery)
    actuals, forecasts = load_window(date(2026, 1, 2), day)
    return decision_hours(actuals, forecasts, day, day, time(9, 0))


def test_16_january_0100_is_the_hand_computed_case():
    chosen = _chosen("2026-01-16")
    publish_times = {format_utc(hour.publish_time) for hour, _actual in chosen}
    assert publish_times == {"2026-01-15T07:30:00Z"}

    hour, actual = next(
        pair for pair in chosen if format_utc(pair[0].start_time) == "2026-01-16T01:00:00Z"
    )
    assert hour.generation == 7008
    assert actual == (7278 + 6890) / 2
    assert actual == 7084
    assert hour.generation - actual == -76


def test_15_january_uses_the_0730_run_and_known_horizon():
    chosen = _chosen("2026-01-15")
    publish_times = {format_utc(hour.publish_time) for hour, _actual in chosen}
    assert publish_times == {"2026-01-14T07:30:00Z"}
    horizons = [hour.horizon_h for hour, _actual in chosen]
    assert min(horizons) == 16.5
    assert max(horizons) == 39.5
