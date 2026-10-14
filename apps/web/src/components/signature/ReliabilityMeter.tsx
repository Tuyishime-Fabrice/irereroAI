"use client";

import { useTranslations } from "next-intl";

/** How much a centre's reports can be relied on: share of clean, on-time weeks. */
export function ReliabilityMeter({ score }: { score: number }) {
  const t = useTranslations("reliability");
  const segments = 5;
  const filled = Math.round(score * segments);
  const level = score >= 0.8 ? "high" : score >= 0.6 ? "medium" : "low";
  const colour = { high: "bg-success", medium: "bg-ochre", low: "bg-danger" }[level];
  return (
    <span
      className="inline-flex items-center gap-2"
      role="meter"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(score * 100)}
      aria-label={t("label")}
    >
      <span aria-hidden className="flex gap-0.5">
        {Array.from({ length: segments }, (_, i) => (
          <span key={i} className={`h-3 w-2 rounded-[1px] ${i < filled ? colour : "bg-line"}`} />
        ))}
      </span>
      <span className="text-xs text-ink-muted">
        <span className="tabular">{Math.round(score * 100)}%</span> · {t(level)}
      </span>
    </span>
  );
}
