"use client";

import { useTranslations } from "next-intl";

import { PageTitle } from "@/components/ui/PageTitle";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { LoadingState } from "@/components/ui/States";
import { api } from "@/lib/api/client";
import { useApi } from "@/lib/useApi";

/** Which model version each engine component runs, and every pipeline run with its checks. */
export function SystemStatus() {
  const t = useTranslations("status");
  const models = useApi("models", async () => (await api.GET("/national/models")).data ?? null);
  const method = useApi(
    "methodology",
    async () => (await api.GET("/public/methodology")).data ?? null,
  );
  if (!models.data || !method.data) return <LoadingState />;
  return (
    <>
      <PageTitle title={t("title")} lead={t("lead")} />
      <div className="grid gap-6 xl:grid-cols-2">
        <Panel>
          <PanelHeader title={t("models")} />
          <ul className="divide-y divide-line">
            {models.data.map((m) => (
              <li key={m.id} className="px-4 py-3 text-sm">
                <p className="font-medium text-ink">
                  {t(`component.${m.component}`)} · <span className="tabular">{m.id}</span>
                </p>
                <p className="text-ink-muted">{m.description}</p>
                <p className="tabular mt-1 text-xs text-ink-muted">{JSON.stringify(m.params)}</p>
                <p className="mt-1 text-xs text-ink-muted">
                  {Object.keys(m.metrics).length ? JSON.stringify(m.metrics) : t("noMetrics")}
                </p>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel>
          <PanelHeader title={t("runs")} />
          <ul className="divide-y divide-line">
            {method.data.runs.map((run) => (
              <li key={run.id} className="px-4 py-3 text-sm">
                <p className="font-medium text-ink">
                  {run.pipeline} · {run.status} · {run.origin} ·{" "}
                  <span className="tabular">{run.code_version}</span>
                </p>
                <p className="tabular text-xs text-ink-muted">
                  {Object.entries(run.row_counts)
                    .map(([k, v]) => `${k} ${v}`)
                    .join(" · ")}
                </p>
                <ul className="mt-1 text-xs">
                  {run.checks.map((c) => (
                    <li key={c.name} className={c.passed ? "text-success" : "text-danger"}>
                      {c.passed ? "✓" : "✗"} {c.detail}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </>
  );
}
