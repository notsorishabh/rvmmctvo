import { useEffect, useState } from "react";
import { getJson, type MetaResponse } from "./api";
import { ControlBar } from "./components/ControlBar";
import { Decision } from "./pages/Decision";
import { ErrorAnalysis } from "./pages/ErrorAnalysis";
import { Overview } from "./pages/Overview";
import { Revisions } from "./pages/Revisions";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "decision", label: "Decision" },
  { id: "error", label: "Error analysis" },
  { id: "revisions", label: "Revisions" },
] as const;

type Tab = (typeof TABS)[number]["id"];

export function App() {
  const [dateFrom, setDateFrom] = useState("2026-01-02");
  const [dateTo, setDateTo] = useState("2026-02-01");
  const [cutoff, setCutoff] = useState("09:00");
  const [day, setDay] = useState("2026-01-15");
  const [tab, setTab] = useState<Tab>("overview");
  const [assumptions, setAssumptions] = useState<string[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    getJson<MetaResponse>("meta", {}, controller.signal)
      .then((meta) => setAssumptions(meta.assumptions))
      .catch(() => setAssumptions([]));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (day < dateFrom) setDay(dateFrom);
    if (day > dateTo) setDay(dateTo);
  }, [dateFrom, dateTo, day]);

  const rangeError = dateFrom > dateTo ? "The start date must be on or before the end date." : null;

  return (
    <div className="app">
      <header className="header">
        <div>
          <p className="eyebrow">GB day-ahead · national wind</p>
          <h1>Wind Forecast Monitor</h1>
          <p>Latest wind forecast at the buying cutoff, and how far it missed.</p>
        </div>
      </header>
      <ControlBar
        dateFrom={dateFrom}
        dateTo={dateTo}
        cutoff={cutoff}
        onFrom={setDateFrom}
        onTo={setDateTo}
        onCutoff={setCutoff}
      />
      <div className="tabs" role="tablist">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            onMouseDown={() => setTab(item.id)}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {rangeError ? <p className="range-error">{rangeError}</p> : null}
      {!rangeError && tab === "overview" ? (
        <Overview dateFrom={dateFrom} dateTo={dateTo} cutoff={cutoff} />
      ) : null}
      {!rangeError && tab === "decision" ? (
        <Decision day={day} dateFrom={dateFrom} dateTo={dateTo} cutoff={cutoff} onDay={setDay} />
      ) : null}
      {!rangeError && tab === "error" ? (
        <ErrorAnalysis dateFrom={dateFrom} dateTo={dateTo} cutoff={cutoff} />
      ) : null}
      {!rangeError && tab === "revisions" ? (
        <Revisions day={day} dateFrom={dateFrom} dateTo={dateTo} cutoff={cutoff} onDay={setDay} />
      ) : null}
      <details className="assumptions">
        <summary>Assumptions</summary>
        <ul>
          {(assumptions.length ? assumptions : ["Times are UTC. January UK time equals UTC."]).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </details>
    </div>
  );
}
