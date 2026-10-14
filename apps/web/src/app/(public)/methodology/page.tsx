import { getTranslations } from "next-intl/server";

import { PipelineSteps } from "@/components/public/PipelineSteps";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { serverApi } from "@/lib/api/server";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  const t = await getTranslations("methodology");
  return { title: t("title") };
}

const STATUS_STYLE = {
  loaded: "border-kivu text-kivu",
  simulated_stand_in: "border-clay text-clay",
  planned: "border-line-strong text-ink-muted",
} as const;

export default async function MethodologyPage() {
  const t = await getTranslations("methodology");
  const { data } = await serverApi.GET("/public/methodology");
  return (
    <>
      <PageTitle title={t("title")} lead={t("lead")} />
      <PipelineSteps />
      <Panel className="mt-10">
        <PanelHeader title={t("sourcesTitle")} />
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-ink-muted">
              <tr>
                <th scope="col" className="px-4 py-2">
                  {t("source")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("today")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("feeds")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("licence")}
                </th>
              </tr>
            </thead>
            <tbody>
              {data?.sources.map((s) => (
                <tr key={s.id} className="border-t border-line align-top">
                  <th scope="row" className="px-4 py-2 font-normal">
                    <span className="font-medium text-ink">{s.name}</span>
                    <span className="block text-xs text-ink-muted">
                      {s.publisher}
                      {s.reference_year ? ` · ${s.reference_year}` : ""}
                    </span>
                  </th>
                  <td className="px-4 py-2">
                    <span
                      className={`inline-block rounded-sm border px-1.5 py-0.5 text-xs ${STATUS_STYLE[s.status]}`}
                    >
                      {t(`status.${s.status}`)}
                    </span>
                  </td>
                  <td className="tabular px-4 py-2 text-xs">{s.feeds.join(", ")}</td>
                  <td className="px-4 py-2 text-xs text-ink-muted">{s.licence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <Panel className="mt-6">
        <PanelHeader title={t("runsTitle")} />
        <ul className="divide-y divide-line">
          {data?.runs.map((run) => (
            <li key={run.id} className="px-4 py-3 text-sm">
              <p className="font-medium text-ink">
                {run.pipeline} · <span className="text-ink-muted">{t(`origin.${run.origin}`)}</span>{" "}
                · <span className="tabular">{run.started_at.slice(0, 16).replace("T", " ")}</span>
              </p>
              <ul className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs">
                {run.checks.map((check) => (
                  <li key={check.name} className={check.passed ? "text-success" : "text-danger"}>
                    {check.passed ? "✓" : "✗"} {check.detail}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </Panel>
    </>
  );
}
