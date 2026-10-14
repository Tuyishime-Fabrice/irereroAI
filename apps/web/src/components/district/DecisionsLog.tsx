"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";

import { PageTitle } from "@/components/ui/PageTitle";
import { Panel } from "@/components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { api } from "@/lib/api/client";
import { useApi } from "@/lib/useApi";

import { useDistrictCode } from "./useDistrict";

export function DecisionsLog() {
  const t = useTranslations("decisionsLog");
  const decision = useTranslations("decision");
  const district = useDistrictCode();
  const log = useApi(
    `decisions:${district}`,
    async () => (await api.GET("/decisions", { params: { query: { district } } })).data ?? null,
  );
  if (log.loading) return <LoadingState />;
  if (log.error || !log.data) return <ErrorState onRetry={log.reload} />;
  return (
    <>
      <PageTitle
        title={t("title")}
        lead={t("lead")}
        actions={
          <Link
            href="/district/brief"
            className="inline-flex min-h-10 items-center rounded-md bg-kivu px-4 text-sm font-medium text-white"
          >
            {t("brief")}
          </Link>
        }
      />
      <Panel className="overflow-x-auto">
        {log.data.length === 0 ? (
          <EmptyState title={t("empty")} />
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-ink-muted">
              <tr>
                <th scope="col" className="px-4 py-2">
                  {t("when")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("who")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("what")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("verdict")}
                </th>
                <th scope="col" className="px-4 py-2">
                  {t("reason")}
                </th>
              </tr>
            </thead>
            <tbody>
              {log.data.map((row, i) => (
                <tr key={i} className="border-t border-line align-top">
                  <td className="tabular px-4 py-2">
                    {row.created_at.slice(0, 16).replace("T", " ")}
                  </td>
                  <td className="px-4 py-2">{row.user_name}</td>
                  <td className="px-4 py-2">
                    {decision(`action.${row.action}`)} · {row.site_name}
                    <span className="block text-xs text-ink-muted">{row.scenario_name}</span>
                  </td>
                  <td className="px-4 py-2">{decision(`verdict.${row.verdict}`)}</td>
                  <td className="px-4 py-2">
                    {row.reason_code ? decision(`reason.${row.reason_code}`) : "–"}
                    {row.reason_text && (
                      <span className="block text-xs text-ink-muted">“{row.reason_text}”</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
      <p className="mt-3 text-sm text-ink-muted">{t("auditNote")}</p>
    </>
  );
}
