"""Decision-time forecast selection against a three-run fixture."""

from datetime import datetime, time

from backend.app.services.decision import ForecastPoint, select_decision_forecast
from backend.app.times import UTC

DELIVERY = datetime(2026, 1, 15, tzinfo=UTC).date()


def _point(publish: str, start: str, generation: float) -> ForecastPoint:
    published = datetime.fromisoformat(publish).replace(tzinfo=UTC)
    starts = datetime.fromisoformat(start).replace(tzinfo=UTC)
    horizon = (starts - published).total_seconds() / 3600.0
    return ForecastPoint(published, starts, generation, horizon)


def _fixture() -> list[ForecastPoint]:
    hours = ("2026-01-15T00:00:00", "2026-01-15T01:00:00")
    runs = (
        ("2026-01-14T04:30:00", (100.0, 110.0)),
        ("2026-01-14T07:30:00", (200.0, 210.0)),
        ("2026-01-14T09:30:00", (300.0, 310.0)),
    )
    rows: list[ForecastPoint] = []
    for published, generations in runs:
        for start, generation in zip(hours, generations):
            rows.append(_point(published, start, generation))
    return rows


def test_cutoff_before_and_after_a_run_picks_the_latest_eligible_run():
    rows = _fixture()

    at_nine = select_decision_forecast(rows, DELIVERY, time(9, 0))
    assert [hour.generation for hour in at_nine] == [200.0, 210.0]
    assert {hour.publish_time for hour in at_nine} == {
        datetime(2026, 1, 14, 7, 30, tzinfo=UTC)
    }

    at_ten = select_decision_forecast(rows, DELIVERY, time(10, 0))
    assert [hour.generation for hour in at_ten] == [300.0, 310.0]
    assert {hour.publish_time for hour in at_ten} == {
        datetime(2026, 1, 14, 9, 30, tzinfo=UTC)
    }


def test_run_published_exactly_at_the_cutoff_is_eligible():
    rows = _fixture()
    chosen = select_decision_forecast(rows, DELIVERY, time(4, 30))
    assert [hour.generation for hour in chosen] == [100.0, 110.0]


def test_run_published_after_the_cutoff_is_never_used():
    rows = _fixture()
    chosen = select_decision_forecast(rows, DELIVERY, time(9, 0))
    assert all(hour.publish_time < datetime(2026, 1, 14, 9, 30, tzinfo=UTC) for hour in chosen)
    assert 300.0 not in [hour.generation for hour in chosen]


def test_later_run_that_misses_an_hour_does_not_hide_the_earlier_run():
    rows = [
        _point("2026-01-14T04:30:00", "2026-01-15T00:00:00", 100.0),
        _point("2026-01-14T04:30:00", "2026-01-15T01:00:00", 110.0),
        _point("2026-01-14T07:30:00", "2026-01-15T00:00:00", 200.0),
    ]
    chosen = select_decision_forecast(rows, DELIVERY, time(9, 0))
    by_hour = {hour.start_time.hour: hour for hour in chosen}
    assert by_hour[0].generation == 200.0
    assert by_hour[0].publish_time == datetime(2026, 1, 14, 7, 30, tzinfo=UTC)
    assert by_hour[1].generation == 110.0
    assert by_hour[1].publish_time == datetime(2026, 1, 14, 4, 30, tzinfo=UTC)


def test_day_with_no_eligible_run_returns_empty():
    rows = _fixture()
    assert select_decision_forecast(rows, DELIVERY, time(4, 0)) == []
    other_day = datetime(2026, 2, 1, tzinfo=UTC).date()
    assert select_decision_forecast(rows, other_day, time(9, 0)) == []
