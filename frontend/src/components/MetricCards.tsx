import type { Metrics, QueryState } from "../api";
import { mw, signedMw } from "../format";

const ERROR_TIP =
  "Error is forecast minus actual. A positive value is an over-forecast.";
const ALIGN_TIP =
  "Each forecast hour is compared with the mean of the actuals at H:00 and H:30. A missing half-hour drops that hour.";

type Card = {
  name: string;
  value: string;
  tip: string;
  tone?: "positive" | "negative";
};

function cards(metrics: Metrics): Card[] {
  const biasTone =
    metrics.bias == null || metrics.bias === 0
      ? undefined
      : metrics.bias > 0
        ? "positive"
        : "negative";
  return [
    { name: "MAE", value: `${mw(metrics.mae)} MW`, tip: ERROR_TIP },
    { name: "NMAE", value: metrics.nmae == null ? "–" : `${mw(metrics.nmae, 1)}%`, tip: "MAE divided by mean actual, in percent." },
    { name: "RMSE", value: `${mw(metrics.rmse)} MW`, tip: ERROR_TIP },
    { name: "Bias", value: `${signedMw(metrics.bias)} MW`, tip: ERROR_TIP, tone: biasTone },
    { name: "P95", value: `${mw(metrics.p95_abs_error)} MW`, tip: "95th percentile of absolute error. " + ERROR_TIP },
  ];
}

export function MetricCards({ state }: { state: QueryState<Metrics> }) {
  if (state.status === "loading") return <p className="state">Loading metrics…</p>;
  if (state.status === "error") return <p className="state state-error">{state.error}</p>;
  if (state.data.n === 0) {
    return <p className="state">No forecast available for this selection.</p>;
  }
  return (
    <>
      <div className="card-grid">
        {cards(state.data).map((card) => (
          <article key={card.name} className="panel metric">
            <div className="name">
              {card.name}
              <span className="tip" tabIndex={0} data-tip={card.tip} aria-label={card.tip}>
                i
              </span>
            </div>
            <strong className={card.tone}>{card.value}</strong>
            <em>{state.data.n.toLocaleString("en-GB")} hours</em>
          </article>
        ))}
      </div>
      <p className="caption">
        Hourly actuals average H:00 and H:30.
        <span className="tip" tabIndex={0} data-tip={ALIGN_TIP} aria-label={ALIGN_TIP}>
          i
        </span>
      </p>
    </>
  );
}
