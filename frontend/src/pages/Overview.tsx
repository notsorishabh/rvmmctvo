import { useEffect, useState } from "react";
import { getJson, type Metrics, type QueryState, type SeriesPoint } from "../api";
import { ChartFrame } from "../components/ChartFrame";
import { MetricCards } from "../components/MetricCards";
import { SeriesChart } from "../components/SeriesChart";

type Props = { dateFrom: string; dateTo: string; cutoff: string };

export function Overview({ dateFrom, dateTo, cutoff }: Props) {
  const metrics = usePair<Metrics>("metrics", dateFrom, dateTo, cutoff);
  const series = usePair<SeriesPoint[]>("series", dateFrom, dateTo, cutoff);
  return (
    <>
      <MetricCards state={metrics} />
      <ChartFrame
        title="Actual vs decision forecast"
        caption="The forecast is the latest run published at or before the cutoff on D-1. Each delivery day uses its own run, so small jumps at midnight are expected. Positive error means an over-forecast."
        state={series}
        empty={series.status === "ok" && series.data.length === 0}
      >
        {series.status === "ok" ? <SeriesChart points={series.data} /> : null}
      </ChartFrame>
    </>
  );
}

function usePair<T>(path: string, dateFrom: string, dateTo: string, cutoff: string): QueryState<T> {
  const [state, setState] = useState<QueryState<T>>({ status: "loading", data: null, error: null });
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading", data: null, error: null });
    getJson<T>(path, { from: dateFrom, to: dateTo, cutoff }, controller.signal)
      .then((data) => setState({ status: "ok", data, error: null }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : "Request failed";
        setState({ status: "error", data: null, error: message });
      });
    return () => controller.abort();
  }, [path, dateFrom, dateTo, cutoff]);
  return state;
}
