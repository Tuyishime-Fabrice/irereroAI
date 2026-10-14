"use client";

import type { FeatureCollection } from "geojson";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useEffect, useState } from "react";

import { PointMap } from "@/components/map/PointMap";
import { useProvenance } from "@/components/shell/ProvenanceProvider";
import { AlertRow } from "@/components/signature/AlertRow";
import { ReliabilityMeter } from "@/components/signature/ReliabilityMeter";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { api } from "@/lib/api/client";

import { useAlerts, useCentres, useSectorCode } from "./useSector";

export function SectorOverview() {
  const t = useTranslations("sector");
  const sector = useSectorCode();
  const centres = useCentres(sector);
  const alerts = useAlerts(sector);
  const [outlines, setOutlines] = useState<FeatureCollection | null>(null);
  useProvenance(centres.data?.provenance);
  useProvenance(alerts.data?.provenance);
  useEffect(() => {
    if (!sector) return;
    // Sector codes are S-<DISTRICT>-<SECTOR>, so the district is part of the code.
    const districtCode = `D-${sector.split("-")[1] ?? ""}`;
    api
      .GET("/public/outlines", { params: { query: { district: districtCode } } })
      .then(({ data }) => {
        if (!data) return;
        setOutlines({
          ...(data as unknown as FeatureCollection),
          features: (data as unknown as FeatureCollection).features.filter((f) => f.id === sector),
        });
      });
  }, [sector]);

  if (!sector) return <EmptyState title={t("pickSector")} />;
  if (centres.loading || alerts.loading) return <LoadingState />;
  if (centres.error || alerts.error || !centres.data || !alerts.data) {
    return (
      <ErrorState
        onRetry={() => {
          centres.reload();
          alerts.reload();
        }}
      />
    );
  }
  const list = centres.data.data;
  const open = alerts.data.data.filter((a) => a.status !== "resolved");
  const severityOf = (code: string) => {
    const levels = open.filter((a) => a.centre_code === code).map((a) => a.severity);
    return levels.includes("critical") ? "alert" : levels.length ? "warning" : "ok";
  };
  const stats = [
    { key: "centres", value: list.length },
    { key: "reported", value: `${list.filter((c) => c.reported_this_week).length}/${list.length}` },
    { key: "openAlerts", value: open.length },
    { key: "missing", value: open.filter((a) => a.kind === "missing_report").length },
  ];

  return (
    <>
      <PageTitle
        title={t("overviewTitle", { sector: list[0]?.sector_name ?? sector })}
        lead={t("overviewLead")}
      />
      <dl className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        {stats.map((s) => (
          <Panel key={s.key} className="p-4">
            <dt className="text-xs text-ink-muted">{t(`stats.${s.key}`)}</dt>
            <dd className="font-display text-3xl text-ink tabular">{s.value}</dd>
          </Panel>
        ))}
      </dl>
      <div className="grid gap-6 xl:grid-cols-[1fr_420px]">
        <div className="flex flex-col gap-6">
          <PointMap
            outlines={outlines}
            points={list.map((c) => ({
              id: c.code,
              lon: c.lon,
              lat: c.lat,
              label: c.name,
              tone: severityOf(c.code),
            }))}
            place={null}
            height={360}
          />
          <Panel>
            <PanelHeader
              title={t("centresTitle")}
              action={
                <Link href="/sector/centres" className="text-sm text-kivu underline">
                  {t("seeAll")}
                </Link>
              }
            />
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-ink-muted">
                <tr>
                  <th scope="col" className="px-4 py-2">
                    {t("centre")}
                  </th>
                  <th scope="col" className="px-4 py-2">
                    {t("thisWeek")}
                  </th>
                  <th scope="col" className="px-4 py-2">
                    {t("reliability")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {list.map((c) => (
                  <tr key={c.code} className="border-t border-line">
                    <th scope="row" className="px-4 py-2 font-normal">
                      <Link href={`/sector/centres/${c.code}`} className="text-kivu underline">
                        {c.name}
                      </Link>
                    </th>
                    <td className="px-4 py-2">
                      {c.reported_this_week ? (
                        t("reported")
                      ) : (
                        <span className="text-ochre-text">{t("notReported")}</span>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      <ReliabilityMeter score={c.reliability_score} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </div>
        <Panel className="self-start">
          <PanelHeader
            title={t("openAlerts")}
            action={
              <Link href="/sector/alerts" className="text-sm text-kivu underline">
                {t("queue")}
              </Link>
            }
          />
          {open.length === 0 ? (
            <EmptyState title={t("noAlerts")} />
          ) : (
            <div className="flex flex-col gap-2 p-3">
              {open.map((alert) => (
                <AlertRow
                  key={alert.id}
                  alert={alert}
                  action={
                    <Link
                      href={`/sector/alerts/${alert.id}`}
                      className="text-sm text-kivu underline"
                    >
                      {t("open")}
                    </Link>
                  }
                />
              ))}
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
