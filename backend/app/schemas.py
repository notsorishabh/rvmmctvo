"""JSON response models."""

from pydantic import BaseModel, Field


class RunDay(BaseModel):
    date: str
    count: int
    publish_times: list[str]


class MetaResponse(BaseModel):
    delivery_from: str
    delivery_to: str
    default_cutoff: str
    timezone_note: str
    assumptions: list[str]
    runs_per_day: list[RunDay]


class SeriesPoint(BaseModel):
    time: str
    actual: float | None
    forecast: float | None
    error: float | None
    run_publish_time: str | None
    horizon_h: float | None


class BandCoverage(BaseModel):
    days: int
    hours: int
    inside: int
    coverage_pct: float | None


class MetricsResponse(BaseModel):
    n: int
    mae: float | None
    rmse: float | None
    bias: float | None
    mape: float | None
    p95_abs_error: float | None
    max_abs_error: float | None
    nmae: float | None = Field(description="MAE / mean(actual), in percent")
    error_p10: float | None
    error_p90: float | None
    band_coverage: BandCoverage


class HourError(BaseModel):
    hour: int
    mae: float | None
    bias: float | None
    n: int


class HorizonError(BaseModel):
    bucket: str
    mae: float | None
    rmse: float | None
    bias: float | None
    n: int


class DecisionHourOut(BaseModel):
    time: str
    forecast: float
    actual: float | None
    error: float | None
    horizon_h: float
    run_publish_time: str
    band_low: float | None
    band_high: float | None


class DecisionResponse(BaseModel):
    date: str
    cutoff: str
    cutoff_ts: str
    message: str | None
    run_publish_time: str | None
    publish_times: list[str]
    horizon_min_h: float | None
    horizon_max_h: float | None
    error_p10: float | None
    error_p90: float | None
    history_days: int
    headline: str | None
    hours: list[DecisionHourOut]


class RevisionPoint(BaseModel):
    time: str
    generation: float
    horizon_h: float


class RevisionRun(BaseModel):
    publish_time: str
    hours: list[RevisionPoint]


class ActualPoint(BaseModel):
    time: str
    actual: float


class RevisionsResponse(BaseModel):
    date: str
    cutoff: str
    cutoff_ts: str
    decision_publish_time: str | None
    message: str | None
    runs: list[RevisionRun]
    actuals: list[ActualPoint]
