"""The error band for day D ignores D itself and every later day."""

from datetime import date

from backend.app.services.band import percentiles_before

DAY = date(2026, 1, 10)


def _history() -> dict[date, list[float]]:
    return {date(2026, 1, day): [100.0] * 24 for day in range(2, 10)}


def test_later_days_do_not_move_the_band():
    quiet = _history()
    quiet[date(2026, 1, 11)] = [100.0] * 24
    huge = _history()
    huge[date(2026, 1, 11)] = [1_000_000.0] * 24
    huge[date(2026, 1, 12)] = [-1_000_000.0] * 24
    huge[DAY] = [1_000_000.0] * 24

    assert percentiles_before(quiet, DAY) == percentiles_before(huge, DAY)
    p10, p90, history_days = percentiles_before(huge, DAY)
    assert history_days == 8
    assert p10 == 100.0
    assert p90 == 100.0


def test_fewer_than_three_prior_days_has_no_band():
    errors = {
        date(2026, 1, 2): [10.0, 20.0],
        date(2026, 1, 3): [30.0],
    }
    assert percentiles_before(errors, date(2026, 1, 4)) == (None, None, 2)
