import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DecisionHour } from "../api";
import { mw, signedMw, utcLabel } from "../format";

type Row = DecisionHour & { label: string; band: [number, number] | null };

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
      <strong>{utcLabel(row.time, false)} UTC</strong>
      <div>Forecast {mw(row.forecast)} MW</div>
      <div>Actual {mw(row.actual)} MW</div>
      <div>Error {signedMw(row.error)} MW (positive = over-forecast)</div>
      <div>
        Band {mw(row.band_low)} to {mw(row.band_high)} MW
      </div>
    </div>
  );
}

export function DecisionChart({ hours }: { hours: DecisionHour[] }) {
  const data: Row[] = hours.map((hour) => ({
    ...hour,
    label: utcLabel(hour.time, false),
    band:
      hour.band_low == null || hour.band_high == null ? null : [hour.band_low, hour.band_high],
  }));
  return (
    <ResponsiveContainer width="100%" height={380}>
      <ComposedChart data={data} margin={{ top: 12, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="#d5e0d8" />
        <XAxis dataKey="label" minTickGap={18} tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} unit=" MW" width={72} />
        <Tooltip content={<Tip />} />
        <Legend />
        <Area
          type="monotone"
          dataKey="band"
          name="Likely range of actual (P10–P90)"
          stroke="none"
          fill="#0c6b58"
          fillOpacity={0.18}
        />
        <Line type="monotone" dataKey="actual" name="Actual" stroke="#1d4e89" dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="forecast" name="Decision forecast" stroke="#0c6b58" dot={false} strokeWidth={2} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
