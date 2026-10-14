"use client";

import { useLocale, useTranslations } from "next-intl";

import { Logo } from "@/components/brand/Logo";
import { useProvenance } from "@/components/shell/ProvenanceProvider";
import { ImpactCounter } from "@/components/signature/ImpactCounter";
import { SimulatedWatermark } from "@/components/signature/SimulatedWatermark";
import { Button } from "@/components/ui/Button";
import { EmptyState, LoadingState } from "@/components/ui/States";
import { api } from "@/lib/api/client";
import { formatRange, formatRwf, formatShare } from "@/lib/format/numbers";
import { useApi } from "@/lib/useApi";

import { useDistrictCode } from "./useDistrict";

/** A printable district brief in the current language. Print or save as PDF from the browser. */
export function DistrictBrief() {
  const t = useTranslations("brief");
  const decision = useTranslations("decision");
  const locale = useLocale();
  const district = useDistrictCode();
  const brief = useApi(`brief:${district}`, async () => {
    const { data, response } = await api.GET("/brief", { params: { query: { district } } });
    return response.ok ? (data ?? null) : null;
  });
  useProvenance(brief.data?.provenance);
  if (brief.loading) return <LoadingState />;
  if (!brief.data) return <EmptyState title={t("noPlan")} />;
  const b = brief.data.data;
  const simulated = brief.data.provenance.origins.includes("simulated");

  return (
    <article className="mx-auto max-w-3xl rounded-md border border-line bg-surface p-8 print:border-0 print:p-0">
      <div className="no-print mb-6 flex justify-end">
        <Button variant="primary" onClick={() => window.print()}>
          {t("print")}
        </Button>
      </div>
      {simulated && <SimulatedWatermark force variant="stamp" />}
      <header className="mt-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-ink-muted">{t("kicker", { week: b.week })}</p>
          <h1 className="font-display text-3xl text-ink">
            {t("title", { district: b.district_name })}
          </h1>
        </div>
        <Logo size={24} />
      </header>
      <section className="mt-6 grid gap-4 sm:grid-cols-4">
        <div>
          <p className="text-xs text-ink-muted">{t("children")}</p>
          <p className="tabular">{formatRange(b.children)}</p>
        </div>
        <div>
          <p className="text-xs text-ink-muted">{t("stunting")}</p>
          <p className="tabular">{formatRange(b.stunting_risk, formatShare)}</p>
        </div>
        <div>
          <p className="text-xs text-ink-muted">{t("alerts")}</p>
          <p className="tabular">{b.open_alerts}</p>
        </div>
        <div>
          <p className="text-xs text-ink-muted">{t("demand")}</p>
          <p className="tabular">{b.demand_signals}</p>
        </div>
      </section>
      <section className="mt-8">
        <h2 className="font-display text-xl text-ink">
          {t("approvedTitle", { plan: b.scenario_name, budget: formatRwf(b.budget_rwf, true) })}
        </h2>
        {b.approved.length === 0 ? (
          <p className="mt-2 text-ink-muted">{t("noneApproved")}</p>
        ) : (
          <ol className="mt-3 flex flex-col gap-4">
            {b.approved.map((r, i) => (
              <li key={r.id} className="border-l-4 border-kivu pl-4">
                <p className="font-semibold text-ink">
                  {i + 1}. {decision(`action.${r.action}`)} · {r.site_name} ({r.sector_name})
                </p>
                <p className="text-sm text-ink">
                  {locale === "rw" ? r.explanation_rw : r.explanation_en}
                </p>
              </li>
            ))}
          </ol>
        )}
      </section>
      <section className="mt-8">
        <ImpactCounter outcomes={b.outcomes} title={t("outcomes")} />
      </section>
      <footer className="mt-8 border-t border-line pt-4 text-xs text-ink-muted">
        <p>{t("decidedBy", { names: b.decided_by.join(", ") || "–" })}</p>
        <p className="mt-1">{t("humans")}</p>
        <p className="mt-2">
          {t("sources")}:{" "}
          {[
            ...new Set(
              brief.data.provenance.sources.map(
                (s) => `${s.source} (${s.reference_year}, ${s.origin})`,
              ),
            ),
          ].join("; ")}
        </p>
      </footer>
    </article>
  );
}
