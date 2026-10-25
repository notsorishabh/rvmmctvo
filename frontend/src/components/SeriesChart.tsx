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
import type { SeriesPoint } from "../api";
import { dayTick, mw, signedMw, utcLabel } from "../format";

type Row = SeriesPoint;

function Tip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: Row }>;
}) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return (
    <div className="panel" style={{ padding: 10 }}>
      <strong>{utcLabel(row.time)} UTC</strong>
      <div>Actual {mw(row.actual)} MW</div>
      <div>Forecast {mw(row.forecast)} MW</div>
      <div>Error {signedMw(row.error)} MW (positive = over-forecast)</div>
      <div>Each delivery day uses its own decision run, so small jumps at midnight are expected.</div>
    </div>
  );
}

export function SeriesChart({ points }: { points: SeriesPoint[] }) {
  const ticks = midnightTicks(points);
  return (
    <ResponsiveContainer width="100%" height={380}>
      <LineChart data={points} margin={{ top: 12, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="#d5e0d8" />
        <XAxis
          dataKey="time"
          ticks={ticks}
          interval={0}
          tickFormatter={dayTick}
          tick={{ fontSize: 12 }}
        />
        <YAxis tick={{ fontSize: 12 }} unit=" MW" width={72} />
        <Tooltip content={<Tip />} />
        <Legend />
        <Line type="monotone" dataKey="actual" name="Actual" stroke="#1d4e89" dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="forecast" name="Decision forecast" stroke="#0c6b58" dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function midnightTicks(points: SeriesPoint[]): string[] {
  return points
    .filter((point) => point.time.endsWith("T00:00:00Z"))
    .filter((_, index) => index % 3 === 0)
    .map((point) => point.time);
}
