import { useEffect, useState } from "react";
import { getJson, type QueryState, type RevisionsResponse } from "../api";
import { ChartFrame } from "../components/ChartFrame";
import { RevisionsChart } from "../components/RevisionsChart";
import { dayLabel } from "../format";

type Props = {
  day: string;
  onDay: (value: string) => void;
  dateFrom: string;
  dateTo: string;
  cutoff: string;
};

export function Revisions({ day, onDay, dateFrom, dateTo, cutoff }: Props) {
  const [state, setState] = useState<QueryState<RevisionsResponse>>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading", data: null, error: null });
    getJson<RevisionsResponse>("revisions", { date: day, cutoff }, controller.signal)
      .then((data) => setState({ status: "ok", data, error: null }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : "Request failed";
        setState({ status: "error", data: null, error: message });
      });
    return () => controller.abort();
  }, [day, cutoff]);

  const data = state.status === "ok" ? state.data : null;
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
      <ChartFrame
        title="All runs covering this delivery day"
        caption="The thick line is the decision run at this cutoff. Grey lines were published after the cutoff. The dark line is the hourly actual (mean of H:00 and H:30). Hover a line for its publish time."
        state={state}
        empty={Boolean(data?.message)}
        emptyText={data?.message ?? "No forecast available for this selection."}
      >
        {data ? <RevisionsChart data={data} /> : null}
      </ChartFrame>
    </>
  );
}
