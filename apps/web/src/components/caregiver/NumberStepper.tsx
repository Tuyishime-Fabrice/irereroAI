"use client";

import { useId } from "react";

/** A count with large minus and plus buttons, readable on a small phone. */
export function NumberStepper({
  label,
  value,
  onChange,
  max = 999,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  max?: number;
}) {
  const id = useId();
  const set = (next: number) => onChange(Math.max(0, Math.min(max, next)));
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-base font-medium text-ink">
        {label}
      </label>
      <div className="flex items-stretch gap-2">
        <button
          type="button"
          onClick={() => set(value - 1)}
          aria-label={`${label}: −1`}
          className="h-14 w-14 shrink-0 rounded-md border border-line-strong bg-surface text-2xl text-ink"
        >
          −
        </button>
        <input
          id={id}
          type="number"
          inputMode="numeric"
          min={0}
          max={max}
          value={Number.isNaN(value) ? "" : value}
          onChange={(e) => set(e.target.value === "" ? 0 : Number(e.target.value))}
          className="tabular h-14 w-full min-w-0 rounded-md border border-line-strong bg-surface px-3 text-center text-2xl text-ink"
        />
        <button
          type="button"
          onClick={() => set(value + 1)}
          aria-label={`${label}: +1`}
          className="h-14 w-14 shrink-0 rounded-md border border-line-strong bg-surface text-2xl text-ink"
        >
          +
        </button>
      </div>
    </div>
  );
}
