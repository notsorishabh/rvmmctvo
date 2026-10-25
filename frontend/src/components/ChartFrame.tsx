import type { ReactNode } from "react";
import type { QueryState } from "../api";

type Props = {
  title: string;
  caption?: string;
  state: QueryState<unknown>;
  empty?: boolean;
  emptyText?: string;
  children: ReactNode;
};

export function ChartFrame({
  title,
  caption,
  state,
  empty = false,
  emptyText = "No forecast available for this selection.",
  children,
}: Props) {
  return (
    <section className="panel chart-card">
      <h2>{title}</h2>
      {caption ? <p className="caption">{caption}</p> : null}
      {state.status === "loading" ? <p className="state">Loading…</p> : null}
      {state.status === "error" ? <p className="state state-error">{state.error}</p> : null}
      {state.status === "ok" && empty ? <p className="state">{emptyText}</p> : null}
      {state.status === "ok" && !empty ? children : null}
    </section>
  );
}
