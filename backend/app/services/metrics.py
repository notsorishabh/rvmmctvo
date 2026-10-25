"""Pure error statistics. No database access.

Error is forecast minus actual. Positive means the forecast was too high.
"""

from dataclasses import dataclass
import math

# Right edge is open, so 12.0h belongs to 12–24h, 24.0h to 24–36h, and so on.
BUCKET_0_12 = "0–12h"
BUCKET_12_24 = "12–24h"
BUCKET_24_36 = "24–36h"
BUCKET_36_48 = "36–48h"
BUCKET_48_PLUS = "48h+"
HORIZON_BUCKETS: tuple[str, ...] = (
    BUCKET_0_12,
    BUCKET_12_24,
    BUCKET_24_36,
    BUCKET_36_48,
    BUCKET_48_PLUS,
)


def horizon_bucket(horizon_h: float) -> str:
    if horizon_h < 12:
        return BUCKET_0_12
    if horizon_h < 24:
        return BUCKET_12_24
    if horizon_h < 36:
        return BUCKET_24_36
    if horizon_h < 48:
        return BUCKET_36_48
    return BUCKET_48_PLUS


def linear_percentile(values: list[float], probability: float) -> float:
    """Type-7 linear percentile. `values` need not be sorted."""
    if not values:
        raise ValueError("percentile of an empty series")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


@dataclass(frozen=True)
class Summary:
    n: int
    mae: float | None
    rmse: float | None
    bias: float | None
    mape: float | None
    p95_abs_error: float | None
    max_abs_error: float | None
    nmae: float | None
    error_p10: float | None
    error_p90: float | None


def empty_summary() -> Summary:
    return Summary(0, None, None, None, None, None, None, None, None, None)


def summarise(pairs: list[tuple[float, float]]) -> Summary:
    """Summarise (forecast, actual) pairs. MAPE skips actual == 0.

    `mape` and `nmae` are percentages. `nmae` is MAE / mean(actual).
    `error_p10` and `error_p90` are percentiles of the signed error.
    """
    if not pairs:
        return empty_summary()

    errors = [forecast - actual for forecast, actual in pairs]
    absolute = [abs(error) for error in errors]
    n = len(errors)
    mae = sum(absolute) / n
    bias = sum(errors) / n
    rmse = math.sqrt(sum(error * error for error in errors) / n)
    mape_terms = [
        abs(forecast - actual) / abs(actual)
        for forecast, actual in pairs
        if actual != 0
    ]
    mape = (sum(mape_terms) / len(mape_terms) * 100.0) if mape_terms else None
    mean_actual = sum(actual for _, actual in pairs) / n
    nmae = (mae / mean_actual * 100.0) if mean_actual != 0 else None
    return Summary(
        n=n,
        mae=mae,
        rmse=rmse,
        bias=bias,
        mape=mape,
        p95_abs_error=linear_percentile(absolute, 0.95),
        max_abs_error=max(absolute),
        nmae=nmae,
        error_p10=linear_percentile(errors, 0.10),
        error_p90=linear_percentile(errors, 0.90),
    )


@dataclass(frozen=True)
class HourStat:
    hour: int
    mae: float | None
    bias: float | None
    n: int


def error_by_hour(pairs: list[tuple[float, float, int]]) -> list[HourStat]:
    """MAE and bias of decision-forecast errors for UTC hours 0–23.

    Each item is (forecast, actual, hour).
    """
    grouped: dict[int, list[tuple[float, float]]] = {hour: [] for hour in range(24)}
    for forecast, actual, hour in pairs:
        grouped[hour].append((forecast, actual))
    stats: list[HourStat] = []
    for hour in range(24):
        summary = summarise(grouped[hour])
        stats.append(HourStat(hour=hour, mae=summary.mae, bias=summary.bias, n=summary.n))
    return stats


@dataclass(frozen=True)
class HorizonStat:
    bucket: str
    mae: float | None
    rmse: float | None
    bias: float | None
    n: int


def error_by_horizon(
    rows: list[tuple[float, float, float]],
) -> list[HorizonStat]:
    """MAE, RMSE, and bias for every run, grouped by horizon bucket.

    Each item is (forecast, actual, horizon_h).
    """
    grouped: dict[str, list[tuple[float, float]]] = {
        bucket: [] for bucket in HORIZON_BUCKETS
    }
    for forecast, actual, horizon_h in rows:
        grouped[horizon_bucket(horizon_h)].append((forecast, actual))
    stats: list[HorizonStat] = []
    for bucket in HORIZON_BUCKETS:
        summary = summarise(grouped[bucket])
        stats.append(
            HorizonStat(
                bucket=bucket,
                mae=summary.mae,
                rmse=summary.rmse,
                bias=summary.bias,
                n=summary.n,
            )
        )
    return stats
