"use client";

import { useTranslations } from "next-intl";
import { useId } from "react";

import type { Schemas } from "@/lib/api/client";

type Weights = Schemas["WeightsIn"];
const KEYS = ["stunting", "readiness", "jobs"] as const;

/** Policy weights. The note makes clear the choice is political, not technical. */
export function WeightsControl({
  value,
  onChange,
}: {
  value: Weights;
  onChange: (w: Weights) => void;
}) {
  const t = useTranslations("plan");
  const id = useId();
  const total = KEYS.reduce((sum, k) => sum + value[k], 0) || 1;
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="mb-1 text-sm font-semibold text-ink">{t("weights")}</legend>
      {KEYS.map((key) => (
        <div key={key} className="flex flex-col gap-1">
          <label htmlFor={`${id}-${key}`} className="flex justify-between text-sm text-ink">
            <span>{t(`weight.${key}`)}</span>
            <span className="tabular text-ink-muted">
              {Math.round((value[key] / total) * 100)}%
            </span>
          </label>
          <input
            id={`${id}-${key}`}
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={value[key]}
            onChange={(e) => onChange({ ...value, [key]: Number(e.target.value) })}
            className="accent-[var(--kivu)]"
          />
          <p className="text-xs text-ink-muted">{t(`weightHelp.${key}`)}</p>
        </div>
      ))}
      <p className="rounded-md border border-ochre bg-paper p-2 text-xs text-ink">
        {t("policyNote")}
      </p>
    </fieldset>
  );
}
