"""HTTP API. Reads the prebuilt database and does not write."""

from datetime import date, time, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import (
    ASSUMPTIONS,
    DEFAULT_CUTOFF,
    DELIVERY_END,
    DELIVERY_START,
    FRONTEND_DIST,
    TIMEZONE_NOTE,
)
from backend.app.schemas import (
    ActualPoint,
    BandCoverage,
    DecisionHourOut,
    DecisionResponse,
    HorizonError,
    HourError,
    MetaResponse,
    MetricsResponse,
    RevisionPoint,
    RevisionRun,
    RevisionsResponse,
    RunDay,
    SeriesPoint,
)
from backend.app.services.band import actual_band, percentiles_before, planning_sentence
from backend.app.services.coverage import Coverage, band_coverage, expanding_band_hours
from backend.app.services.decision import cutoff_timestamp
from backend.app.services.metrics import Summary
from backend.app.services.report import (
    day_actuals,
    decision_hours,
    full_range,
    horizon_breakdown,
    hour_breakdown,
    load_window,
    revisions_for,
    runs_per_day,
    summary_for,
)
from backend.app.times import format_utc, parse_hhmm

app = FastAPI(title="Wind Forecast Monitor", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _bad(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


def _parse_day(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise _bad(f"{field} must be YYYY-MM-DD") from error


def _in_scope(day: date, field: str) -> date:
    earliest = date.fromisoformat(DELIVERY_START)
    latest = date.fromisoformat(DELIVERY_END)
    if day < earliest or day > latest:
        raise _bad(f"{field} must be between {DELIVERY_START} and {DELIVERY_END}")
    return day


def _range(
    date_from: str | None,
    date_to: str | None,
    cutoff: str | None,
) -> tuple[date, time, date]:
    earliest, latest = full_range()
    start = earliest if not date_from else _in_scope(_parse_day(date_from, "from"), "from")
    end = latest if not date_to else _in_scope(_parse_day(date_to, "to"), "to")
    if start > end:
        raise _bad("from must be on or before to")
    try:
        clock = parse_hhmm(cutoff or DEFAULT_CUTOFF)
    except ValueError as error:
        raise _bad(str(error)) from error
    return start, clock, end


def _metrics(summary: Summary, coverage: Coverage) -> MetricsResponse:
    return MetricsResponse(
        n=summary.n,
        mae=summary.mae,
        rmse=summary.rmse,
        bias=summary.bias,
        mape=summary.mape,
        p95_abs_error=summary.p95_abs_error,
        max_abs_error=summary.max_abs_error,
        nmae=summary.nmae,
        error_p10=summary.error_p10,
        error_p90=summary.error_p90,
        band_coverage=BandCoverage(
            days=coverage.days,
            hours=coverage.hours,
            inside=coverage.inside,
            coverage_pct=coverage.coverage_pct,
        ),
    )


@app.get("/api/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    return MetaResponse(
        delivery_from=DELIVERY_START,
        delivery_to=DELIVERY_END,
        default_cutoff=DEFAULT_CUTOFF,
        timezone_note=TIMEZONE_NOTE,
        assumptions=list(ASSUMPTIONS),
        runs_per_day=[RunDay(**row) for row in runs_per_day()],
    )


@app.get("/api/series", response_model=list[SeriesPoint])
def series(
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    cutoff: str | None = Query(default=None),
) -> list[SeriesPoint]:
    start, clock, end = _range(date_from, date_to, cutoff)
    actuals, forecasts = load_window(start, end)
    points: list[SeriesPoint] = []
    for hour, actual in decision_hours(actuals, forecasts, start, end, clock):
        error = None if actual is None else hour.generation - actual
        points.append(
            SeriesPoint(
                time=format_utc(hour.start_time),
                actual=actual,
                forecast=hour.generation,
                error=error,
                run_publish_time=format_utc(hour.publish_time),
                horizon_h=hour.horizon_h,
            )
        )
    return points


@app.get("/api/metrics", response_model=MetricsResponse)
def metrics(
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    cutoff: str | None = Query(default=None),
) -> MetricsResponse:
    start, clock, end = _range(date_from, date_to, cutoff)
    history_start = date.fromisoformat(DELIVERY_START)
    actuals, forecasts = load_window(history_start, end)
    history = decision_hours(actuals, forecasts, history_start, end, clock)
    chosen = [(hour, actual) for hour, actual in history if start <= hour.start_time.date() <= end]
    coverage = band_coverage(expanding_band_hours(history, start, end))
    return _metrics(summary_for(chosen), coverage)


@app.get("/api/error-by-hour", response_model=list[HourError])
def error_by_hour_route(
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    cutoff: str | None = Query(default=None),
) -> list[HourError]:
    start, clock, end = _range(date_from, date_to, cutoff)
    actuals, forecasts = load_window(start, end)
    chosen = decision_hours(actuals, forecasts, start, end, clock)
    return [
        HourError(hour=row.hour, mae=row.mae, bias=row.bias, n=row.n)
        for row in hour_breakdown(chosen)
    ]


@app.get("/api/error-by-horizon", response_model=list[HorizonError])
def error_by_horizon_route(
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    cutoff: str | None = Query(default=None),
) -> list[HorizonError]:
    """All forecast runs in the delivery window. Cutoff is accepted and ignored."""
    start, _clock, end = _range(date_from, date_to, cutoff)
    actuals, forecasts = load_window(start, end)
    return [
        HorizonError(bucket=row.bucket, mae=row.mae, rmse=row.rmse, bias=row.bias, n=row.n)
        for row in horizon_breakdown(actuals, forecasts)
    ]


def _clock(cutoff: str | None) -> time:
    try:
        return parse_hhmm(cutoff or DEFAULT_CUTOFF)
    except ValueError as error:
        raise _bad(str(error)) from error


def _history_for(day: date, clock: time):
    """Errors from delivery days strictly before `day`, at this cutoff."""
    scope_start = date.fromisoformat(DELIVERY_START)
    actuals, forecasts = load_window(scope_start, day)
    prior_end = day - timedelta(days=1)
    history = (
        decision_hours(actuals, forecasts, scope_start, prior_end, clock)
        if prior_end >= scope_start
        else []
    )
    errors_by_day: dict[date, list[float]] = {}
    for hour, actual in history:
        if actual is None:
            continue
        errors_by_day.setdefault(hour.start_time.date(), []).append(hour.generation - actual)
    error_p10, error_p90, history_days = percentiles_before(errors_by_day, day)
    chosen = decision_hours(actuals, forecasts, day, day, clock)
    return chosen, error_p10, error_p90, history_days


@app.get("/api/decision", response_model=DecisionResponse)
def decision(
    delivery: str | None = Query(default=None, alias="date"),
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
    cutoff: str | None = Query(default=None),
) -> DecisionResponse:
    """`from` and `to` are accepted and ignored. The band uses days before `date` only."""
    if not delivery:
        raise _bad("date is required (YYYY-MM-DD)")
    day = _in_scope(_parse_day(delivery, "date"), "date")
    if date_from or date_to:
        _range(date_from, date_to, cutoff)
    clock = _clock(cutoff)
    chosen, error_p10, error_p90, history_days = _history_for(day, clock)
    return _decision_body(day, clock, chosen, error_p10, error_p90, history_days)


def _decision_body(
    day: date,
    clock: time,
    chosen,
    error_p10: float | None,
    error_p90: float | None,
    history_days: int,
) -> DecisionResponse:
    cutoff_ts = cutoff_timestamp(day, clock)
    headline = None
    if error_p10 is not None and error_p90 is not None:
        headline = planning_sentence(error_p10, error_p90)
    if not chosen:
        return DecisionResponse(
            date=day.isoformat(),
            cutoff=clock.strftime("%H:%M"),
            cutoff_ts=format_utc(cutoff_ts),
            message="no forecast available",
            run_publish_time=None,
            publish_times=[],
            horizon_min_h=None,
            horizon_max_h=None,
            error_p10=error_p10,
            error_p90=error_p90,
            history_days=history_days,
            headline=headline,
            hours=[],
        )
    publish_times = sorted({format_utc(hour.publish_time) for hour, _actual in chosen})
    horizons = [hour.horizon_h for hour, _actual in chosen]
    hours: list[DecisionHourOut] = []
    for hour, actual in chosen:
        error = None if actual is None else hour.generation - actual
        if error_p10 is None or error_p90 is None:
            low, high = None, None
        else:
            low, high = actual_band(hour.generation, error_p10, error_p90)
        hours.append(
            DecisionHourOut(
                time=format_utc(hour.start_time),
                forecast=hour.generation,
                actual=actual,
                error=error,
                horizon_h=hour.horizon_h,
                run_publish_time=format_utc(hour.publish_time),
                band_low=low,
                band_high=high,
            )
        )
    return DecisionResponse(
        date=day.isoformat(),
        cutoff=clock.strftime("%H:%M"),
        cutoff_ts=format_utc(cutoff_ts),
        message=None,
        run_publish_time=publish_times[-1],
        publish_times=publish_times,
        horizon_min_h=min(horizons),
        horizon_max_h=max(horizons),
        error_p10=error_p10,
        error_p90=error_p90,
        history_days=history_days,
        headline=headline,
        hours=hours,
    )


@app.get("/api/revisions", response_model=RevisionsResponse)
def revisions(
    delivery: str | None = Query(default=None, alias="date"),
    cutoff: str | None = Query(default=None),
) -> RevisionsResponse:
    if not delivery:
        raise _bad("date is required (YYYY-MM-DD)")
    day = _in_scope(_parse_day(delivery, "date"), "date")
    clock = _clock(cutoff)
    cutoff_ts = cutoff_timestamp(day, clock)
    actuals, forecasts = load_window(day, day)
    chosen = decision_hours(actuals, forecasts, day, day, clock)
    decision_publish = None
    if chosen:
        decision_publish = max(format_utc(hour.publish_time) for hour, _actual in chosen)
    grouped = revisions_for(actuals, forecasts, day)
    runs = [
        RevisionRun(
            publish_time=format_utc(published),
            hours=[
                RevisionPoint(
                    time=format_utc(point.start_time),
                    generation=point.generation,
                    horizon_h=point.horizon_h,
                )
                for point in points
            ],
        )
        for published, points in grouped.items()
    ]
    observed = [
        ActualPoint(time=format_utc(stamp), actual=value)
        for stamp, value in day_actuals(actuals, day)
    ]
    message = None if runs else "no forecast available"
    return RevisionsResponse(
        date=day.isoformat(),
        cutoff=clock.strftime("%H:%M"),
        cutoff_ts=format_utc(cutoff_ts),
        decision_publish_time=decision_publish,
        message=message,
        runs=runs,
        actuals=observed,
    )


def _mount_frontend(directory: Path) -> None:
    assets = directory / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(directory / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        candidate = (directory / full_path).resolve()
        if candidate.is_file() and directory.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(directory / "index.html")


if FRONTEND_DIST.is_dir():
    _mount_frontend(FRONTEND_DIST)
