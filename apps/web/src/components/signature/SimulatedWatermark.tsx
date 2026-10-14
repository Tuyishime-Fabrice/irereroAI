"use client";

import { useTranslations } from "next-intl";

import { useVisibleOrigins } from "@/components/shell/ProvenanceProvider";

/**
 * The honesty label. `pill` sits in the top bar whenever simulated records are on screen;
 * `stamp` marks printed pages; `inline` labels a single number or card.
 */
export function SimulatedWatermark({
  variant = "pill",
  force = false,
}: {
  variant?: "pill" | "stamp" | "inline";
  force?: boolean;
}) {
  const t = useTranslations("provenance");
  const simulated = useVisibleOrigins().includes("simulated");
  if (!simulated && !force) return null;
  if (variant === "stamp") {
    return (
      <p
        role="note"
        className="border-y-2 border-clay py-1 text-center font-mono text-sm font-semibold tracking-widest text-clay uppercase"
      >
        {t("simulatedStamp")}
      </p>
    );
  }
  if (variant === "inline") {
    return (
      <span className="inline-flex items-center rounded-sm border border-clay px-1.5 font-mono text-[11px] font-semibold tracking-wider text-clay uppercase">
        {t("simulatedShort")}
      </span>
    );
  }
  return (
    <span
      role="status"
      title={t("simulatedExplain")}
      className="inline-flex items-center gap-1.5 rounded-full border-2 border-clay bg-surface px-3 py-0.5 font-mono text-xs font-semibold tracking-widest text-clay uppercase"
    >
      <span aria-hidden className="h-2 w-2 rotate-45 bg-clay" />
      {t("simulatedPill")}
    </span>
  );
}
