"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { useProvenance } from "@/components/shell/ProvenanceProvider";
import { DecisionCard } from "@/components/signature/DecisionCard";
import { ImpactCounter } from "@/components/signature/ImpactCounter";
import { Button } from "@/components/ui/Button";
import { SelectField, TextField } from "@/components/ui/Field";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { EmptyState, LoadingState } from "@/components/ui/States";
import { api, type Schemas } from "@/lib/api/client";
import { formatRwf } from "@/lib/format/numbers";
import { useApi } from "@/lib/useApi";

import { useDistrictCode } from "./useDistrict";
import { WeightsControl } from "./WeightsControl";

type Scenario = Schemas["Envelope_ScenarioOut_"];

export function PlanWorkspace() {
  const t = useTranslations("plan");
  const district = useDistrictCode();
  const defaults = useApi(
    `defaults:${district}`,
    async () =>
      (await api.GET("/planning-defaults/{area}", { params: { path: { area: district } } })).data ??
      null,
  );
  const history = useApi(
    `scenarios:${district}`,
    async () => (await api.GET("/scenarios", { params: { query: { district } } })).data ?? null,
  );
  const [budget, setBudget] = useState<number | null>(null);
  const [weights, setWeights] = useState<Schemas["WeightsIn"] | null>(null);
  const [name, setName] = useState("");
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [running, setRunning] = useState(false);
  const [failed, setFailed] = useState(false);
  useProvenance(scenario?.provenance);

  const latest = history.data?.[0]?.id;
  useEffect(() => {
    if (!latest || scenario) return;
    let active = true;
    api
      .GET("/scenarios/{scenario_id}", { params: { path: { scenario_id: latest } } })
      .then(({ data }) => {
        if (active && data) setScenario(data);
      });
    return () => {
      active = false;
    };
  }, [latest, scenario]);

  if (defaults.loading || history.loading) return <LoadingState />;
  const currentBudget = budget ?? defaults.data?.budget_rwf ?? 120_000_000;
  const currentWeights = weights ??
    defaults.data?.weights ?? { stunting: 0.4, readiness: 0.4, jobs: 0.2 };

  async function run() {
    setRunning(true);
    setFailed(false);
    const { data } = await api.POST("/scenarios", {
      body: {
        district_code: district,
        name: name.trim() || t("defaultName", { n: (history.data?.length ?? 0) + 1 }),
        budget_rwf: currentBudget,
        weights: currentWeights,
        excluded_site_ids: [],
      },
    });
    setRunning(false);
    if (!data) {
      setFailed(true);
      return;
    }
    setScenario(data);
    history.reload();
  }

  async function open(id: string) {
    const { data } = await api.GET("/scenarios/{scenario_id}", {
      params: { path: { scenario_id: id } },
    });
    if (data) setScenario(data);
  }

  const plan = scenario?.data;
  const places = plan?.recommendations.filter((r) => r.action !== "support") ?? [];
  const support = plan?.recommendations.filter((r) => r.action === "support") ?? [];
  const maxReached = Math.max(1, ...places.map((r) => r.children_reached.high));
  // Numbered within each list, so the shortlist starts at 1 even when support actions ranked first.
  const card = (rec: Schemas["RecommendationOut"], index: number) => (
    <DecisionCard
      key={rec.id}
      recommendation={{ ...rec, rank: index + 1 }}
      maxReached={maxReached}
      canDecide
      onDecide={async (decision) => {
        const { data } = await api.POST("/recommendations/{recommendation_id}/decision", {
          params: { path: { recommendation_id: rec.id } },
          body: decision,
        });
        if (!data) throw new Error("not saved");
        setScenario(data);
        history.reload();
      }}
    />
  );

  return (
    <>
      <PageTitle title={t("title")} lead={t("lead")} />
      <div className="grid gap-6 xl:grid-cols-[320px_1fr]">
        <div className="flex flex-col gap-4">
          <Panel className="flex flex-col gap-4 p-4">
            <TextField
              label={t("budget")}
              inputMode="numeric"
              value={String(currentBudget)}
              onChange={(e) => setBudget(Number(e.target.value.replace(/\D/g, "")) || 0)}
              hint={formatRwf(currentBudget, true)}
            />
            <WeightsControl value={currentWeights} onChange={setWeights} />
            <TextField
              label={t("name")}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("namePlaceholder")}
            />
            <Button
              variant="primary"
              size="lg"
              onClick={run}
              disabled={running || currentBudget <= 0}
            >
              {running ? t("running") : t("run")}
            </Button>
            {failed && (
              <p role="alert" className="text-sm text-danger">
                {t("failed")}
              </p>
            )}
            <p className="text-xs text-ink-muted">{t("runNote")}</p>
          </Panel>
          {history.data && history.data.length > 0 && (
            <Panel className="p-4">
              <SelectField
                label={t("history")}
                value={plan?.id ?? ""}
                onChange={(e) => open(e.target.value)}
              >
                {history.data.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} · {t("historyCounts", { approved: s.approved, rejected: s.rejected })}
                  </option>
                ))}
              </SelectField>
            </Panel>
          )}
        </div>

        <div className="flex flex-col gap-6">
          {!plan ? (
            <Panel>
              <EmptyState title={t("empty")}>{t("emptyText")}</EmptyState>
            </Panel>
          ) : (
            <>
              <Panel className="p-4">
                <ImpactCounter
                  outcomes={plan.outcomes}
                  compareTo={plan.baseline}
                  title={t("impactTitle", { name: plan.name })}
                />
                <p className="mt-2 text-xs text-ink-muted">
                  {t("baselineNote", {
                    reached: Math.round(plan.baseline.children_reached.estimate),
                    risk: Math.round(plan.baseline.high_risk_reached.estimate),
                  })}
                </p>
              </Panel>
              <section aria-labelledby="shortlist">
                <h2 id="shortlist" className="mb-3 font-display text-xl text-ink">
                  {t("shortlist")}
                </h2>
                <div className="grid gap-4 2xl:grid-cols-2">{places.map(card)}</div>
              </section>
              {support.length > 0 && (
                <section aria-labelledby="small">
                  <h2 id="small" className="mb-1 font-display text-xl text-ink">
                    {t("smallActions")}
                  </h2>
                  <p className="mb-3 text-sm text-ink-muted">{t("smallNote")}</p>
                  <div className="grid gap-4 2xl:grid-cols-2">{support.map(card)}</div>
                </section>
              )}
              {plan.rejected.length > 0 && (
                <details className="rounded-md border border-line bg-surface">
                  <summary className="cursor-pointer px-4 py-3 font-semibold text-ink">
                    {t("rejected", { n: plan.rejected.length })}
                  </summary>
                  <div className="grid gap-4 p-4 2xl:grid-cols-2">{plan.rejected.map(card)}</div>
                </details>
              )}
              <Panel>
                <PanelHeader title={t("method")} />
                <p className="p-4 text-sm text-ink-muted">
                  {t("methodText", {
                    minutes: plan.catchment_minutes,
                    version: plan.optimizer_version,
                  })}
                </p>
              </Panel>
            </>
          )}
        </div>
      </div>
    </>
  );
}
