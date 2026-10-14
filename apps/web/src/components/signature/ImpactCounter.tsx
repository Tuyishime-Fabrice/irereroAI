"use client";

import { useTranslations } from "next-intl";

import type { Schemas } from "@/lib/api/client";
import { formatRange, formatRwf } from "@/lib/format/numbers";

type Outcomes = Schemas["OutcomesOut"];

/** What a plan would change, in countable outcomes only. Never a stunting reduction. */
export function ImpactCounter({
  outcomes,
  title,
  compareTo,
}: {
  outcomes: Outcomes;
  title?: string;
  compareTo?: Outcomes | null;
}) {
  const t = useTranslations("impact");
  const rows: { key: string; value: string; delta?: number }[] = [
    {
      key: "reached",
      value: formatRange(outcomes.children_reached),
      delta: compareTo
        ? outcomes.children_reached.estimate - compareTo.children_reached.estimate
        : undefined,
    },
    { key: "uncovered", value: formatRange(outcomes.uncovered_remaining) },
    {
      key: "highRisk",
      value: formatRange(outcomes.high_risk_reached),
      delta: compareTo
        ? outcomes.high_risk_reached.estimate - compareTo.high_risk_reached.estimate
        : undefined,
    },
    {
      key: "mothers",
      value: formatRange(outcomes.mothers_under3_reached),
      delta: compareTo
        ? outcomes.mothers_under3_reached.estimate - compareTo.mothers_under3_reached.estimate
        : undefined,
    },
    {
      key: "supported",
      value: formatRange({
        estimate: outcomes.children_supported,
        low: outcomes.children_supported,
        high: outcomes.children_supported,
      }),
    },
    { key: "cost", value: formatRwf(outcomes.cost_rwf, true) },
  ];
  return (
    <figure className="flex flex-col gap-3">
      {title && <figcaption className="text-sm font-semibold text-ink">{title}</figcaption>}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
        {rows.map((row) => (
          <div key={row.key} className="flex flex-col">
            <dt className="text-xs text-ink-muted">{t(row.key)}</dt>
            <dd className="font-display text-xl text-ink">
              <span className="tabular text-[18px]">{row.value}</span>
              {row.delta !== undefined && Math.round(row.delta) !== 0 && (
                <span
                  className={`ml-2 font-mono text-xs ${row.delta > 0 ? "text-success" : "text-danger"}`}
                >
                  {row.delta > 0 ? "+" : "−"}
                  {Math.abs(Math.round(row.delta))} {t("vsBaseline")}
                </span>
              )}
            </dd>
          </div>
        ))}
      </dl>
      <p className="border-t border-line pt-2 text-xs text-ink-muted">{t("countableOnly")}</p>
    </figure>
  );
}
