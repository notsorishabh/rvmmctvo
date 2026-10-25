import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { RevisionsResponse } from "../api";
import { cutoffLabel, mw, utcLabel } from "../format";

type Group = "decision" | "earlier" | "later";

const GROUP_NAME: Record<Group, string> = {
  decision: "Decision run",
  earlier: "Earlier runs",
  later: "Later runs",
};

export function RevisionsChart({ data }: { data: RevisionsResponse }) {
  const rows = data.actuals.map((actual) => {
    const row: Record<string, string | number | null> = {
      label: utcLabel(actual.time, false),
      actual: actual.actual,
    };
    for (const run of data.runs) {
      const point = run.hours.find((hour) => hour.time === actual.time);
      row[run.publish_time] = point ? point.generation : null;
    }
    return row;
  });
  const seen = new Set<Group>();

  return (
    <>
      <p className="caption">Cutoff: {cutoffLabel(data.cutoff_ts)}</p>
      <ResponsiveContainer width="100%" height={420}>
        <LineChart data={rows} margin={{ top: 12, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid stroke="#d5e0d8" />
          <XAxis dataKey="label" minTickGap={16} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} unit=" MW" width={72} />
          <Tooltip content={<Tip decision={data.decision_publish_time} cutoff={data.cutoff_ts} />} />
          <Legend />
          <Line type="monotone" dataKey="actual" name="Actual" stroke="#172229" strokeWidth={2.4} dot={false} />
          {data.runs.map((run) => {
            const group = runGroup(run.publish_time, data.decision_publish_time, data.cutoff_ts);
            const first = !seen.has(group);
            seen.add(group);
            return (
              <Line
                key={run.publish_time}
                type="monotone"
                dataKey={run.publish_time}
                name={GROUP_NAME[group]}
                stroke={strokeFor(group)}
                strokeWidth={group === "decision" ? 3 : 1.3}
                dot={false}
                connectNulls={false}
                legendType={first ? "line" : "none"}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </>
  );
}

function Tip({
  active,
  payload,
  decision,
  cutoff,
}: {
  active?: boolean;
  payload?: ReadonlyArray<{ dataKey?: string | number; value?: number | string | null }>;
  decision: string | null;
  cutoff: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="panel" style={{ padding: 10 }}>
      {payload.map((item) => {
        const key = String(item.dataKey ?? "");
        if (item.value == null || item.value === "") return null;
        if (key === "actual") {
          return <div key={key}>Actual {mw(Number(item.value))} MW</div>;
        }
        const group = runGroup(key, decision, cutoff);
        return (
          <div key={key}>
            {GROUP_NAME[group]} · {utcLabel(key)} UTC · {mw(Number(item.value))} MW
          </div>
        );
      })}
    </div>
  );
}

function runGroup(publishTime: string, decision: string | null, cutoff: string): Group {
  if (decision && publishTime === decision) return "decision";
  if (publishTime > cutoff) return "later";
  return "earlier";
}

function strokeFor(group: Group): string {
  if (group === "decision") return "#0c6b58";
  if (group === "later") return "#c5d0cc";
  return "#1d4e89";
}
