"""Half-hour actuals average onto the forecast hour."""

from datetime import datetime, timedelta

from backend.app.services.align import align_hours, hourly_actual
from backend.app.times import UTC


def test_half_hour_pair_averages():
    hour = datetime(2026, 1, 2, 0, tzinfo=UTC)
    actuals = {
        hour: 100.0,
        hour + timedelta(minutes=30): 300.0,
    }
    assert hourly_actual(actuals, hour) == 200.0
    assert align_hours(actuals, [hour]) == [(hour, 200.0)]


def test_missing_half_hour_drops_the_hour():
    hour = datetime(2026, 1, 2, 5, tzinfo=UTC)
    only_on_the_hour = {hour: 100.0}
    only_half_past = {hour + timedelta(minutes=30): 100.0}
    assert hourly_actual(only_on_the_hour, hour) is None
    assert hourly_actual(only_half_past, hour) is None
    assert align_hours(only_on_the_hour, [hour, hour + timedelta(hours=1)]) == []


def test_complete_hour_is_kept_when_a_neighbour_is_incomplete():
    hour = datetime(2026, 1, 2, 5, tzinfo=UTC)
    nxt = hour + timedelta(hours=1)
    actuals = {
        hour: 10.0,
        hour + timedelta(minutes=30): 30.0,
        nxt: 80.0,
    }
    assert align_hours(actuals, [hour, nxt]) == [(hour, 20.0)]
