import { ReactNode } from "react";

export interface Option<T extends string> {
  value: T;
  label: string;
  hint?: string;
  icon: ReactNode;
}

/** Selectable card used for goal / sex / activity / persona steps. */
export function OptionCard<T extends string>({
  option,
  selected,
  index,
  onSelect,
}: {
  option: Option<T>;
  selected: boolean;
  index: number;
  onSelect: (v: T) => void;
}) {
  return (
    <button
      type="button"
      className={`opt ${selected ? "opt--on" : ""}`}
      style={{ animationDelay: `${0.06 * index}s` }}
      onClick={() => onSelect(option.value)}
      aria-pressed={selected}
    >
      <span className="opt__icon" aria-hidden="true">
        {option.icon}
      </span>
      <span className="opt__text">
        <span className="opt__label">{option.label}</span>
        {option.hint && <span className="opt__hint">{option.hint}</span>}
      </span>
      <span className="opt__check" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="16" height="16">
          <path d="M5 12.5l4.2 4.2L19 7" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    </button>
  );
}

/** Big animated number readout backed by a range slider. */
export function SliderField({
  label,
  value,
  min,
  max,
  step = 1,
  unit,
  format,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit: string;
  format?: (v: number) => string;
  onChange: (v: number) => void;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div className="slider">
      <div className="slider__head">
        <span className="slider__label">{label}</span>
        <span className="slider__value">
          <b>{format ? format(value) : value}</b>
          <em>{unit}</em>
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ "--fill": `${pct}%` } as React.CSSProperties}
        className="slider__input"
      />
    </div>
  );
}
