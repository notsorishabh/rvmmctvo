"""Actual band is forecast minus the error percentiles, clamped at 0."""

from backend.app.services.band import actual_band, planning_sentence


def test_wide_positive_error_puts_the_band_below_the_forecast():
    low, high = actual_band(10_000, error_p10=-500, error_p90=4_000)
    assert low == 6_000
    assert high == 10_500


def test_symmetric_error_is_symmetric_around_the_forecast():
    low, high = actual_band(10_000, error_p10=-1_000, error_p90=1_000)
    assert low == 9_000
    assert high == 11_000


def test_band_low_is_clamped_at_zero():
    low, _high = actual_band(3_000, error_p10=-500, error_p90=4_000)
    assert low == 0


def test_sentence_for_mixed_signs():
    assert planning_sentence(-549, 4_098) == (
        "At this cutoff, actual wind has typically landed "
        "between 4,098 MW below and 549 MW above the forecast (80% of hours)."
    )


def test_sentence_when_the_forecast_runs_high_throughout():
    assert planning_sentence(500, 4_000) == (
        "At this cutoff, actual wind has typically landed "
        "between 500 and 4,000 MW below the forecast (80% of hours)."
    )


def test_sentence_when_the_forecast_runs_low_throughout():
    assert planning_sentence(-2_000, -400) == (
        "At this cutoff, actual wind has typically landed "
        "between 400 and 2,000 MW above the forecast (80% of hours)."
    )
