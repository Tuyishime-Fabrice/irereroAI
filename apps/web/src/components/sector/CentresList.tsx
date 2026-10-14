"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";

import { useProvenance } from "@/components/shell/ProvenanceProvider";
import { ReliabilityMeter } from "@/components/signature/ReliabilityMeter";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel } from "@/components/ui/Panel";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { formatNumber } from "@/lib/format/numbers";

import { useCentres, useSectorCode } from "./useSector";

export function CentresList() {
  const t = useTranslations("sector");
  const find = useTranslations("find");
  const centres = useCentres(useSectorCode());
  useProvenance(centres.data?.provenance);
  if (centres.loading) return <LoadingState />;
  if (centres.error || !centres.data) return <ErrorState onRetry={centres.reload} />;
  return (
    <>
      <PageTitle title={t("centresTitle")} lead={t("centresLead")} />
      <Panel className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-ink-muted">
            <tr>
              <th scope="col" className="px-4 py-2">
                {t("centre")}
              </th>
              <th scope="col" className="px-4 py-2">
                {t("type")}
              </th>
              <th scope="col" className="px-4 py-2">
                {t("capacity")}
              </th>
              <th scope="col" className="px-4 py-2">
                {t("enrolled")}
              </th>
              <th scope="col" className="px-4 py-2">
                {t("lastReport")}
              </th>
              <th scope="col" className="px-4 py-2">
                {t("verifiedCol")}
              </th>
              <th scope="col" className="px-4 py-2">
                {t("reliability")}
              </th>
            </tr>
          </thead>
          <tbody>
            {centres.data.data.map((c) => (
              <tr key={c.code} className="border-t border-line">
                <th scope="row" className="px-4 py-2 font-normal">
                  <Link href={`/sector/centres/${c.code}`} className="text-kivu underline">
                    {c.name}
                  </Link>
                  <span className="block text-xs text-ink-muted tabular">{c.code}</span>
                </th>
                <td className="px-4 py-2">{find(`type.${c.type}`)}</td>
                <td className="tabular px-4 py-2">{c.capacity}</td>
                <td className="tabular px-4 py-2">{formatNumber(c.latest_enrolled)}</td>
                <td className="tabular px-4 py-2">{c.last_report_week ?? "–"}</td>
                <td className="px-4 py-2">
                  {c.verified ? t("yes") : <span className="text-ochre-text">{t("no")}</span>}
                </td>
                <td className="px-4 py-2">
                  <ReliabilityMeter score={c.reliability_score} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </>
  );
}
