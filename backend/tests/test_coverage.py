"""Hand-made band coverage: 4 hours, 3 inside."""

from datetime import date

from backend.app.services.coverage import band_coverage


def test_four_hours_three_inside_is_75_percent():
    day = date(2026, 1, 10)
    rows = [
        (day, 100.0, 90.0, 110.0),
        (day, 80.0, 90.0, 110.0),
        (day, 100.0, 90.0, 110.0),
        (day, 105.0, 90.0, 110.0),
    ]
    result = band_coverage(rows)
    assert result.days == 1
    assert result.hours == 4
    assert result.inside == 3
    assert result.coverage_pct == 75.0


def test_edges_of_the_band_count_as_inside():
    day = date(2026, 1, 10)
    rows = [
        (day, 90.0, 90.0, 110.0),
        (day, 110.0, 90.0, 110.0),
    ]
    result = band_coverage(rows)
    assert result.inside == 2
    assert result.coverage_pct == 100.0


def test_empty_rows_have_no_percentage():
    result = band_coverage([])
    assert result.days == 0
    assert result.hours == 0
    assert result.inside == 0
    assert result.coverage_pct is None
