import { useEffect, useState } from "react";
import {
  getJson,
  type HorizonError,
  type HourError,
  type QueryState,
  type SeriesPoint,
} from "../api";
import { ChartFrame } from "../components/ChartFrame";
import { ErrorHistogram, HorizonChart, HourChart } from "../components/ErrorCharts";

type Props = { dateFrom: string; dateTo: string; cutoff: string };

export function ErrorAnalysis({ dateFrom, dateTo, cutoff }: Props) {
  const hours = useGet<HourError[]>("error-by-hour", dateFrom, dateTo, cutoff);
  const horizons = useGet<HorizonError[]>("error-by-horizon", dateFrom, dateTo, cutoff);
  const series = useGet<SeriesPoint[]>("series", dateFrom, dateTo, cutoff);
  const hourEmpty = hours.status === "ok" && hours.data.every((row) => row.n === 0);
  const horizonEmpty = horizons.status === "ok" && horizons.data.every((row) => row.n === 0);
  const seriesEmpty = series.status === "ok" && series.data.every((row) => row.error == null);

  return (
    <div className="stack">
      <ChartFrame
        title="Error by hour of day"
        caption="Decision-forecast MAE and bias for each UTC hour. Positive bias means the forecast ran high."
        state={hours}
        empty={hourEmpty}
      >
        {hours.status === "ok" ? <HourChart rows={hours.data} /> : null}
      </ChartFrame>
      <ChartFrame
        title="Error by horizon"
        caption="Every forecast run in the window, not only the decision run. 12.0 h sits in 12–24 h."
        state={horizons}
        empty={horizonEmpty}
      >
        {horizons.status === "ok" ? <HorizonChart rows={horizons.data} /> : null}
      </ChartFrame>
      <ChartFrame
        title="Error histogram"
        caption="Decision-forecast errors in MW. Bars to the right of zero are over-forecasts."
        state={series}
        empty={seriesEmpty}
      >
        {series.status === "ok" ? <ErrorHistogram points={series.data} /> : null}
      </ChartFrame>
    </div>
  );
}

function useGet<T>(path: string, dateFrom: string, dateTo: string, cutoff: string): QueryState<T> {
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
