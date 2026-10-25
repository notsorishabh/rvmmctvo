"""Hand-computed errors for a four-pair series."""

import math

from backend.app.services.metrics import (
    BUCKET_0_12,
    BUCKET_12_24,
    BUCKET_24_36,
    BUCKET_36_48,
    BUCKET_48_PLUS,
    horizon_bucket,
    summarise,
)


# (forecast, actual) -> errors 2, -3, 0, 2
PAIRS = [(10.0, 8.0), (12.0, 15.0), (0.0, 0.0), (7.0, 5.0)]


def test_known_arrays_match_hand_computed_metrics():
    summary = summarise(PAIRS)
    assert summary.n == 4
    assert summary.mae == 1.75
    assert summary.bias == 0.25
    assert summary.rmse == math.sqrt(4.25)
    assert summary.max_abs_error == 3.0
    # Sorted absolute errors [0, 2, 2, 3]; position (4-1)*0.95 = 2.85.
    assert summary.p95_abs_error == 2.0 * 0.15 + 3.0 * 0.85
    # Actual 0 is skipped: (0.25 + 0.2 + 0.4) / 3 * 100.
    assert math.isclose(summary.mape, (0.85 / 3.0) * 100.0)
    # nmae = 1.75 / mean(8, 15, 0, 5) * 100.
    assert summary.nmae == 25.0
    # Signed errors sorted [-3, 0, 2, 2].
    assert summary.error_p10 == -3.0 * 0.7 + 0.0 * 0.3
    assert summary.error_p90 == 2.0


def test_mape_skips_actual_zero_and_is_absent_when_every_actual_is_zero():
    summary = summarise([(5.0, 0.0), (4.0, 0.0)])
    assert summary.n == 2
    assert summary.mape is None
    assert summary.nmae is None


def test_empty_pairs_return_null_metrics():
    summary = summarise([])
    assert summary.n == 0
    assert summary.mae is None
    assert summary.p95_abs_error is None


def test_horizon_bucket_edges():
    assert horizon_bucket(0.0) == BUCKET_0_12
    assert horizon_bucket(11.999) == BUCKET_0_12
    assert horizon_bucket(12.0) == BUCKET_12_24
    assert horizon_bucket(23.999) == BUCKET_12_24
    assert horizon_bucket(24.0) == BUCKET_24_36
    assert horizon_bucket(36.0) == BUCKET_36_48
    assert horizon_bucket(47.999) == BUCKET_36_48
    assert horizon_bucket(48.0) == BUCKET_48_PLUS
    assert horizon_bucket(72.5) == BUCKET_48_PLUS
