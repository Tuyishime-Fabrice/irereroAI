"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { ImpactCounter } from "@/components/signature/ImpactCounter";
import { SimulatedWatermark } from "@/components/signature/SimulatedWatermark";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel } from "@/components/ui/Panel";
import { LoadingState } from "@/components/ui/States";
import { api, type Schemas } from "@/lib/api/client";
import { formatRwf } from "@/lib/format/numbers";

import { useDistrictCode } from "./useDistrict";
import { WeightsControl } from "./WeightsControl";

type Option = { budget: number; weights: Schemas["WeightsIn"] };
const START: Option[] = [
  { budget: 120_000_000, weights: { stunting: 0.4, readiness: 0.4, jobs: 0.2 } },
  { budget: 120_000_000, weights: { stunting: 0.8, readiness: 0.1, jobs: 0.1 } },
  { budget: 60_000_000, weights: { stunting: 0.2, readiness: 0.2, jobs: 0.6 } },
];

/** Up to three budgets and weightings side by side, plus the population-first baseline. */
export function WhatIf() {
  const t = useTranslations("whatIf");
  const district = useDistrictCode();
  const [options, setOptions] = useState<Option[]>(START);
  const [results, setResults] = useState<(Schemas["SimulationOut"] | null)[] | null>(null);
  const [busy, setBusy] = useState(false);

  async function compare() {
    setBusy(true);
    const outcomes = await Promise.all(
      options.map(
        async (option, i) =>
          (
            await api.POST("/simulate", {
              body: {
                district_code: district,
                budget_rwf: option.budget,
                weights: option.weights,
                include_baseline: i === 0,
              },
            })
          ).data ?? null,
      ),
    );
    setResults(outcomes);
    setBusy(false);
  }

  const baseline = results?.[0]?.baseline ?? null;
  return (
    <>
      <PageTitle
        title={t("title")}
        lead={t("lead")}
        actions={<SimulatedWatermark force variant="inline" />}
      />
      <div className="grid gap-4 lg:grid-cols-3">
        {options.map((option, i) => (
          <Panel key={i} className="flex flex-col gap-4 p-4">
            <h2 className="font-display text-xl text-ink">{t("option", { n: i + 1 })}</h2>
            <TextField
              label={t("budget")}
              inputMode="numeric"
              value={String(option.budget)}
              hint={formatRwf(option.budget, true)}
              onChange={(e) =>
                setOptions(
                  options.map((o, j) =>
                    j === i ? { ...o, budget: Number(e.target.value.replace(/\D/g, "")) || 0 } : o,
                  ),
                )
              }
            />
            <WeightsControl
              value={option.weights}
              onChange={(w) =>
                setOptions(options.map((o, j) => (j === i ? { ...o, weights: w } : o)))
              }
            />
            {busy && <LoadingState />}
            {results?.[i] && <ImpactCounter outcomes={results[i].outcomes} compareTo={baseline} />}
          </Panel>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-4">
        <Button variant="primary" size="lg" onClick={compare} disabled={busy}>
          {t("compare")}
        </Button>
        <p className="text-sm text-ink-muted">{t("nothingSaved")}</p>
      </div>
      {baseline && (
        <Panel className="mt-6 p-4">
          <ImpactCounter outcomes={baseline} title={t("baseline")} />
          <p className="mt-2 text-xs text-ink-muted">{t("baselineExplain")}</p>
        </Panel>
      )}
    </>
  );
}
