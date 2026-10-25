"""Print where the positive wind-forecast bias comes from.

This script only reads the database. It does not adjust forecasts or metrics.
"""

from datetime import date, time
from statistics import mean

from backend.app.config import DELIVERY_END, DELIVERY_START
from backend.app.services.align import hourly_actual
from backend.app.services.metrics import HORIZON_BUCKETS, horizon_bucket
from backend.app.services.report import decision_hours, load_window


def main() -> None:
    start = date.fromisoformat(DELIVERY_START)
    end = date.fromisoformat(DELIVERY_END)
    actuals, forecasts = load_window(start, end)
    chosen = decision_hours(actuals, forecasts, start, end, time(9, 0))

    by_day: dict[date, list[float]] = {}
    forecast_sum = 0.0
    actual_sum = 0.0
    for hour, actual in chosen:
        if actual is None:
            continue
        error = hour.generation - actual
        by_day.setdefault(hour.start_time.date(), []).append(error)
        forecast_sum += hour.generation
        actual_sum += actual

    print("mean error by delivery day (decision forecast, cutoff 09:00)")
    daily_means: list[float] = []
    for day in sorted(by_day):
        value = mean(by_day[day])
        daily_means.append(value)
        print(f"  {day.isoformat()}  n={len(by_day[day]):2d}  mean_error={value:8.1f} MW")

    print("\nmean error by horizon bucket (every run, not only the decision run)")
    bucket_errors: dict[str, list[float]] = {bucket: [] for bucket in HORIZON_BUCKETS}
    for point in forecasts:
        actual = hourly_actual(actuals, point.start_time)
        if actual is None:
            continue
        bucket_errors[horizon_bucket(point.horizon_h)].append(point.generation - actual)
    bucket_means: list[float] = []
    for bucket in HORIZON_BUCKETS:
        errors = bucket_errors[bucket]
        value = mean(errors) if errors else float("nan")
        bucket_means.append(value)
        print(f"  {bucket:8s}  n={len(errors):5d}  mean_error={value:8.1f} MW")

    latest: dict = {}
    for point in forecasts:
        current = latest.get(point.start_time)
        if current is None or point.publish_time > current.publish_time:
            latest[point.start_time] = point
    short: list[float] = []
    for point in latest.values():
        if not 0 < point.horizon_h <= 3:
            continue
        actual = hourly_actual(actuals, point.start_time)
        if actual is None:
            continue
        short.append(point.generation - actual)
    short_mean = mean(short) if short else float("nan")
    print(
        f"\nlast run before each delivery hour, horizon 0–3h: "
        f"n={len(short)}  mean_error={short_mean:8.1f} MW"
    )

    ratio = forecast_sum / actual_sum if actual_sum else float("nan")
    print(f"\nsum(decision forecast) / sum(actual) = {ratio:.4f}")
    print(f"overall mean decision error = {mean(daily_means):.1f} MW across {len(daily_means)} days")

    positive_days = sum(value > 0 for value in daily_means)
    positive_buckets = sum(value > 0 for value in bucket_means)
    daily_spread = max(daily_means) - min(daily_means) if daily_means else 0.0
    horizon_spread = max(bucket_means) - min(bucket_means) if bucket_means else 0.0
    days_same_sign = bool(daily_means) and (min(daily_means) > 0 or max(daily_means) < 0)
    horizons_level = (
        positive_buckets == len(bucket_means)
        and short_mean > 0
        and horizon_spread < 800
    )
    print("\nconclusion:")
    if days_same_sign and horizons_level:
        print(
            "  The bias is positive on every delivery day and stays in a similar range "
            "at every horizon, including a 0–3h lead. It is likely a systematic data "
            "property (for example different capacity coverage or curtailment), not a bug."
        )
    elif horizons_level:
        print(
            "  Across horizons the bias is a level shift: every bucket is positive and "
            f"the means sit between {min(bucket_means):.0f} and {max(bucket_means):.0f} MW, "
            f"and the last run before each hour (0–3h) is {short_mean:.0f} MW. "
            f"It is not constant from day to day: {positive_days} of {len(daily_means)} days "
            f"are positive, and daily means run from {min(daily_means):.0f} to "
            f"{max(daily_means):.0f} MW (spread {daily_spread:.0f} MW). "
            "That horizon pattern is unlikely to be an off-by-one in one lead time. "
            "It fits a systematic data property, such as capacity coverage or curtailment, "
            "with real day-to-day weather error on top. No correction was applied."
        )
    else:
        print(
            "  The bias is not steady across days and horizons, so it should not be "
            "described as a single data property without a closer look."
        )


if __name__ == "__main__":
    main()
