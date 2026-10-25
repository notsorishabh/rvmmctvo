export const DELIVERY_FROM = "2026-01-02";
export const DELIVERY_TO = "2026-02-01";

export type SeriesPoint = {
  time: string;
  actual: number | null;
  forecast: number | null;
  error: number | null;
  run_publish_time: string | null;
  horizon_h: number | null;
};

export type BandCoverage = {
  days: number;
  hours: number;
  inside: number;
  coverage_pct: number | null;
};

export type Metrics = {
  n: number;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  mape: number | null;
  p95_abs_error: number | null;
  max_abs_error: number | null;
  nmae: number | null;
  error_p10: number | null;
  error_p90: number | null;
  band_coverage: BandCoverage;
};

export type HourError = {
  hour: number;
  mae: number | null;
  bias: number | null;
  n: number;
};

export type HorizonError = {
  bucket: string;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  n: number;
};

export type DecisionHour = {
  time: string;
  forecast: number;
  actual: number | null;
  error: number | null;
  horizon_h: number;
  run_publish_time: string;
  band_low: number | null;
  band_high: number | null;
};

export type DecisionResponse = {
  date: string;
  cutoff: string;
  cutoff_ts: string;
  message: string | null;
  run_publish_time: string | null;
  publish_times: string[];
  horizon_min_h: number | null;
  horizon_max_h: number | null;
  error_p10: number | null;
  error_p90: number | null;
  history_days: number;
  headline: string | null;
  hours: DecisionHour[];
};

export type RevisionsResponse = {
  date: string;
  cutoff: string;
  cutoff_ts: string;
  decision_publish_time: string | null;
  message: string | null;
  runs: {
    publish_time: string;
    hours: { time: string; generation: number; horizon_h: number }[];
  }[];
  actuals: { time: string; actual: number }[];
};

export type MetaResponse = {
  delivery_from: string;
  delivery_to: string;
  default_cutoff: string;
  timezone_note: string;
  assumptions: string[];
  runs_per_day: { date: string; count: number; publish_times: string[] }[];
};

export type QueryState<T> =
  | { status: "loading"; data: null; error: null }
  | { status: "ok"; data: T; error: null }
  | { status: "error"; data: null; error: string };

export async function getJson<T>(
  path: string,
  params: Record<string, string>,
  signal?: AbortSignal,
): Promise<T> {
  const query = new URLSearchParams(params);
  const response = await fetch(`/api/${path}?${query.toString()}`, { signal });
  if (!response.ok) {
    let detail = response.statusText || "Request failed";
    try {
      const body: { detail?: unknown } = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}
