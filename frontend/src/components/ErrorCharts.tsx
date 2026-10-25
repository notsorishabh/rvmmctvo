import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HorizonError, HourError, SeriesPoint } from "../api";
import { hourLabel, mw, signedMw } from "../format";

function HourTip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: HourError & { label: string } }>;
}) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return (
    <div className="panel" style={{ padding: 10 }}>
      <strong>{row.label} UTC</strong>
      <div>MAE {mw(row.mae)} MW</div>
      <div>Bias {signedMw(row.bias)} MW (positive = over-forecast)</div>
      <div>{row.n} hours</div>
    </div>
  );
}

function HorizonTip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: HorizonError }>;
}) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return (
    <div className="panel" style={{ padding: 10 }}>
      <strong>{row.bucket}</strong>
      <div>MAE {mw(row.mae)} MW</div>
      <div>RMSE {mw(row.rmse)} MW</div>
      <div>Bias {signedMw(row.bias)} MW (positive = over-forecast)</div>
      <div>{row.n} pairs, all runs</div>
    </div>
  );
}

export function HourChart({ rows }: { rows: HourError[] }) {
  const data = rows.map((row) => ({ ...row, label: hourLabel(row.hour) }));
  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={data} margin={{ top: 12, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="#d5e0d8" />
        <XAxis dataKey="label" tick={{ fontSize: 12 }} interval={1} />
        <YAxis tick={{ fontSize: 12 }} unit=" MW" width={72} />
        <Tooltip content={<HourTip />} />
        <Legend />
        <Bar dataKey="mae" name="MAE" fill="#0c6b58" radius={[4, 4, 0, 0]} />
        <Line type="monotone" dataKey="bias" name="Bias" stroke="#b5471d" strokeWidth={2} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function HorizonChart({ rows }: { rows: HorizonError[] }) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={rows} margin={{ top: 12, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="#d5e0d8" />
        <XAxis dataKey="bucket" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} unit=" MW" width={72} />
        <Tooltip content={<HorizonTip />} />
        <Legend />
        <Bar dataKey="mae" name="MAE" fill="#1d4e89" radius={[4, 4, 0, 0]} />
        <Bar dataKey="bias" name="Bias" fill="#b5471d" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ErrorHistogram({ points }: { points: SeriesPoint[] }) {
  const errors = points
    .map((point) => point.error)
    .filter((error): error is number => error != null);
  const bins = histogram(errors, 16);
  const xs = bins.map((bin) => bin.x);
  const domainMin = Math.min(0, ...xs);
  const domainMax = Math.max(0, ...xs);
  return (
    <>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={bins} margin={{ top: 12, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid stroke="#d5e0d8" />
          <XAxis
            dataKey="x"
            type="number"
            domain={[domainMin, domainMax]}
            tickFormatter={(value) => mw(Number(value), 0)}
            tick={{ fontSize: 11 }}
          />
          <YAxis tick={{ fontSize: 12 }} allowDecimals={false} width={40} />
          <Tooltip formatter={(value) => [`${value} hours`, "Hours"]} labelFormatter={(value) => `${mw(Number(value), 0)} MW`} />
          <ReferenceLine x={0} stroke="#172229" strokeWidth={2} />
          <Bar dataKey="n" name="Hours" fill="#0c6b58" barSize={18} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div className="hist-sides">
        <span>Under-forecast</span>
        <span>Over-forecast</span>
      </div>
    </>
  );
}

function histogram(errors: number[], count: number): { x: number; n: number }[] {
  if (errors.length === 0) return [];
  const min = Math.min(...errors);
  const max = Math.max(...errors);
  const width = (max - min) / count || 1;
  const buckets = Array.from({ length: count }, (_, index) => ({
    x: min + (index + 0.5) * width,
    n: 0,
  }));
  for (const error of errors) {
    let index = Math.floor((error - min) / width);
    if (index >= count) index = count - 1;
    if (index < 0) index = 0;
    buckets[index].n += 1;
  }
  return buckets;
}
