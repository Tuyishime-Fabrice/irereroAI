"use client";

import { useTranslations } from "next-intl";

import { PageTitle } from "@/components/ui/PageTitle";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { LoadingState } from "@/components/ui/States";
import { api } from "@/lib/api/client";
import { useApi } from "@/lib/useApi";

/** Every pipeline run: input files with checksums, rows written and checks. */
export function Pipelines() {
  const t = useTranslations("admin");
  const method = useTranslations("methodology");
  const runs = useApi(
    "admin:runs",
    async () => (await api.GET("/admin/pipeline-runs")).data ?? null,
  );
  const sources = useApi(
    "methodology",
    async () => (await api.GET("/public/methodology")).data ?? null,
  );
  if (!runs.data || !sources.data) return <LoadingState />;
  return (
    <>
      <PageTitle title={t("pipelinesTitle")} lead={t("pipelinesLead")} />
      <div className="flex flex-col gap-6">
        {runs.data.map((run) => (
          <Panel key={run.id}>
            <PanelHeader
              title={
                <>
                  {run.pipeline} ·{" "}
                  <span className="tabular font-normal text-ink-muted">
                    {run.started_at.slice(0, 19).replace("T", " ")}
                  </span>
                </>
              }
              action={
                <span
                  className={
                    run.status === "succeeded" ? "text-sm text-success" : "text-sm text-danger"
                  }
                >
                  {run.status}
                </span>
              }
            />
            <div className="grid gap-4 p-4 text-sm lg:grid-cols-3">
              <div>
                <p className="text-xs text-ink-muted">{t("inputs")}</p>
                <ul className="tabular text-xs">
                  {run.inputs.length === 0 && <li>–</li>}
                  {run.inputs.map((input) => (
                    <li key={String(input.path)}>
                      {String(input.path)} · {String(input.sha256).slice(0, 12)}…
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-xs text-ink-muted">{t("rows")}</p>
                <ul className="tabular text-xs">
                  {Object.entries(run.row_counts).map(([table, n]) => (
                    <li key={table}>
                      {table}: {n}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-xs text-ink-muted">{t("checks")}</p>
                <ul className="text-xs">
                  {run.checks.map((c) => (
                    <li key={String(c.name)} className={c.passed ? "text-success" : "text-danger"}>
                      {c.passed ? "✓" : "✗"} {String(c.detail)}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Panel>
        ))}
        <Panel>
          <PanelHeader title={method("sourcesTitle")} />
          <ul className="divide-y divide-line">
            {sources.data.sources.map((s) => (
              <li key={s.id} className="flex flex-wrap justify-between gap-2 px-4 py-2 text-sm">
                <span>
                  <span className="tabular text-xs text-ink-muted">{s.id}</span> · {s.name}
                </span>
                <span className="text-xs">{method(`status.${s.status}`)}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </>
  );
}
