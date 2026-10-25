import { useEffect, useState } from "react";
import { getJson, type DecisionResponse, type Metrics, type QueryState } from "../api";
import { ChartFrame } from "../components/ChartFrame";
import { DecisionChart } from "../components/DecisionChart";
import { dayLabel, mw, signedMw, utcLabel } from "../format";

type Props = {
  day: string;
  dateFrom: string;
  dateTo: string;
  cutoff: string;
  onDay: (value: string) => void;
};

export function Decision({ day, dateFrom, dateTo, cutoff, onDay }: Props) {
  const [state, setState] = useState<QueryState<DecisionResponse>>({
    status: "loading",
    data: null,
    error: null,
  });
  const [coverage, setCoverage] = useState<QueryState<Metrics>>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading", data: null, error: null });
    getJson<DecisionResponse>("decision", { date: day, cutoff }, controller.signal)
      .then((data) => setState({ status: "ok", data, error: null }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : "Request failed";
        setState({ status: "error", data: null, error: message });
      });
    return () => controller.abort();
  }, [day, cutoff]);

  useEffect(() => {
    const controller = new AbortController();
    setCoverage({ status: "loading", data: null, error: null });
    getJson<Metrics>("metrics", { from: dateFrom, to: dateTo, cutoff }, controller.signal)
      .then((data) => setCoverage({ status: "ok", data, error: null }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : "Request failed";
        setCoverage({ status: "error", data: null, error: message });
      });
    return () => controller.abort();
  }, [dateFrom, dateTo, cutoff]);

  const data = state.status === "ok" ? state.data : null;
  const enoughHistory = (data?.history_days ?? 0) >= 3;

  return (
    <>
      <div className="day-row">
        <label className="field">
          <span>Delivery day</span>
          <input
            type="date"
            min={dateFrom}
            max={dateTo}
            value={day}
            onChange={(event) => onDay(event.target.value)}
          />
          <em className="date-help">{dayLabel(day)}</em>
        </label>
      </div>
      {data && !data.message && !enoughHistory ? (
        <p className="plan">Not enough history yet ({data.history_days} days)</p>
      ) : null}
      {data && !data.message && enoughHistory && data.headline ? (
        <p className="plan">{data.headline}</p>
      ) : null}
      <BacktestLine state={coverage} />
      {data && !data.message ? (
        <div className="facts">
          <span>Run used {data.run_publish_time ? utcLabel(data.run_publish_time) + " UTC" : "–"}</span>
          <span>
            Horizon {mw(data.horizon_min_h, 1)}–{mw(data.horizon_max_h, 1)} h
          </span>
          {enoughHistory ? <span>Based on {data.history_days} prior days</span> : null}
          {data.error_p10 != null && data.error_p90 != null ? (
            <span>
              Historical error P10 {signedMw(data.error_p10)} MW / P90 {signedMw(data.error_p90)} MW
            </span>
          ) : null}
          {data.publish_times.length > 1 ? <span>{data.publish_times.length} runs fill this day</span> : null}
        </div>
      ) : null}
      <ChartFrame
        title="Forecast, actual, and likely range"
        caption="The shaded area is where the actual is likely to land: forecast minus P90 of the error, up to forecast minus P10. Positive error means an over-forecast. The hourly actual is the mean of H:00 and H:30."
        state={state}
        empty={Boolean(data?.message) || data?.hours.length === 0}
        emptyText={data?.message ?? "No forecast available for this selection."}
      >
        {data ? <DecisionChart hours={data.hours} /> : null}
      </ChartFrame>
    </>
  );
}

function BacktestLine({ state }: { state: QueryState<Metrics> }) {
  if (state.status !== "ok") return null;
  const band = state.data.band_coverage;
  if (band.coverage_pct == null || band.hours === 0) return null;
  const pct = Number.isInteger(band.coverage_pct)
    ? String(band.coverage_pct)
    : band.coverage_pct.toFixed(1);
  return (
    <p className="backtest">
      Backtest: {pct}% of actual hours landed inside the band ({band.hours} hours, {band.days}{" "}
      days).
    </p>
  );
}
