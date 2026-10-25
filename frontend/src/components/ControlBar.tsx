import { useRef } from "react";
import { DELIVERY_FROM, DELIVERY_TO } from "../api";
import { dayLabel } from "../format";

const PRESETS: { value: string; label: string }[] = [
  { value: "09:00", label: "09:00" },
  { value: "09:20", label: "09:20 EPEX GB" },
  { value: "09:50", label: "09:50 N2EX" },
];

type Props = {
  dateFrom: string;
  dateTo: string;
  cutoff: string;
  onFrom: (value: string) => void;
  onTo: (value: string) => void;
  onCutoff: (value: string) => void;
};

export function ControlBar({ dateFrom, dateTo, cutoff, onFrom, onTo, onCutoff }: Props) {
  const presetClick = useRef(false);
  return (
    <div className="panel controls">
      <label className="field">
        <span>Delivery from</span>
        <input
          type="date"
          min={DELIVERY_FROM}
          max={DELIVERY_TO}
          value={dateFrom}
          onChange={(event) => onFrom(event.target.value)}
        />
        <em className="date-help">{dayLabel(dateFrom)}</em>
      </label>
      <label className="field">
        <span>Delivery to</span>
        <input
          type="date"
          min={DELIVERY_FROM}
          max={DELIVERY_TO}
          value={dateTo}
          onChange={(event) => onTo(event.target.value)}
        />
        <em className="date-help">{dayLabel(dateTo)}</em>
      </label>
      <div className="field">
        <span>Cutoff on D-1</span>
        <div className="presets">
          {PRESETS.map((preset) => (
            <button
              key={preset.value}
              type="button"
              aria-pressed={cutoff === preset.value}
              onMouseDown={() => {
                // Apply on press. A blur from the time input can drop the later click.
                presetClick.current = true;
                onCutoff(preset.value);
                window.setTimeout(() => {
                  presetClick.current = false;
                }, 250);
              }}
              onClick={() => onCutoff(preset.value)}
            >
              {preset.label}
            </button>
          ))}
          <input
            type="time"
            value={cutoff}
            aria-label="Cutoff time"
            onChange={(event) => {
              if (presetClick.current) return;
              onCutoff(event.target.value);
            }}
          />
        </div>
      </div>
      <span className="utc-pill" title="January UK time equals UTC">
        Times are UTC
      </span>
    </div>
  );
}
