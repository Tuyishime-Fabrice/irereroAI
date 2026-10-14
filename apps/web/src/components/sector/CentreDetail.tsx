"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useState } from "react";

import { useProvenance } from "@/components/shell/ProvenanceProvider";
import { AlertRow } from "@/components/signature/AlertRow";
import { ReliabilityMeter } from "@/components/signature/ReliabilityMeter";
import { SourceChips } from "@/components/signature/SourceChip";
import { TrendChart } from "@/components/signature/TrendChart";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { useMyCentre } from "@/components/caregiver/useMyCentre";
import { api, type Schemas } from "@/lib/api/client";

export function CentreDetail({ code }: { code: string }) {
  const t = useTranslations("sector");
  const reportT = useTranslations("report");
  const loaded = useMyCentre(code);
  const [override, setOverride] = useState<Schemas["Envelope_CentreDetail_"] | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const detail = override ?? loaded.data;
  useProvenance(detail?.provenance);
  if (loaded.loading && !detail) return <LoadingState />;
  if (!detail) return <ErrorState onRetry={loaded.reload} />;
  const c = detail.data;
  const trend = c.reports.map((r, i) => ({
    label: `${i + 1}`,
    enrolled:
      r.enrolled_0_2_female + r.enrolled_0_2_male + r.enrolled_3_6_female + r.enrolled_3_6_male,
    attendance: r.avg_daily_attendance,
  }));

  async function verify() {
    setBusy(true);
    const { data } = await api.POST("/centres/{code}/verify", {
      params: { path: { code } },
      body: { note: note || null },
    });
    if (data) setOverride(data);
    setBusy(false);
  }

  return (
    <>
      <Link href="/sector/centres" className="text-sm text-kivu underline">
        ← {t("centresTitle")}
      </Link>
      <div className="mt-3">
        <PageTitle
          title={c.name}
          lead={`${c.code} · ${c.sector_name}`}
          actions={
            !c.reported_this_week && (
              <Link
                href={`/sector/centres/${c.code}/report`}
                className="inline-flex min-h-10 items-center rounded-md bg-kivu px-4 text-sm font-medium text-white"
              >
                {t("assistedReport")}
              </Link>
            )
          }
        />
      </div>
      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <div className="flex flex-col gap-6">
          {c.alerts
            .filter((a) => a.status !== "resolved")
            .map((a) => (
              <AlertRow
                key={a.id}
                alert={a}
                action={
                  <Link href={`/sector/alerts/${a.id}`} className="text-sm text-kivu underline">
                    {t("open")}
                  </Link>
                }
              />
            ))}
          <Panel>
            <PanelHeader title={t("trend")} />
            <div className="p-4">
              <TrendChart
                title={t("trend")}
                data={trend}
                series={[
                  { key: "enrolled", label: t("enrolled"), colour: "var(--ink)" },
                  { key: "attendance", label: t("attendance"), colour: "var(--kivu)" },
                ]}
              />
            </div>
          </Panel>
          <Panel className="overflow-x-auto">
            <PanelHeader title={t("allReports")} />
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-ink-muted">
                <tr>
                  <th scope="col" className="px-4 py-2">
                    {t("weekCol")}
                  </th>
                  <th scope="col" className="px-4 py-2">
                    {t("enrolled")}
                  </th>
                  <th scope="col" className="px-4 py-2">
                    {t("attendance")}
                  </th>
                  <th scope="col" className="px-4 py-2">
                    {t("channel")}
                  </th>
                  <th scope="col" className="px-4 py-2">
                    {t("flags")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {[...c.reports].reverse().map((r) => (
                  <tr key={r.week_start} className="border-t border-line">
                    <td className="tabular px-4 py-2">{r.week_start}</td>
                    <td className="tabular px-4 py-2">
                      {r.enrolled_0_2_female +
                        r.enrolled_0_2_male +
                        r.enrolled_3_6_female +
                        r.enrolled_3_6_male}
                    </td>
                    <td className="tabular px-4 py-2">{r.avg_daily_attendance}</td>
                    <td className="px-4 py-2">{t(`channels.${r.channel}`)}</td>
                    <td className="px-4 py-2 text-xs">
                      {r.quality_flags.length ? (
                        <span className="text-ochre-text">
                          {r.quality_flags.map((f) => t(`flag.${f}`)).join(" · ")}
                        </span>
                      ) : (
                        "–"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </div>
        <div className="flex flex-col gap-4">
          <Panel className="flex flex-col gap-3 p-4">
            <h2 className="font-semibold text-ink">{t("verification")}</h2>
            <p className="text-sm text-ink">
              {c.verified
                ? t("verifiedOn", { date: c.verified_at?.slice(0, 10) ?? "" })
                : t("notVerifiedYet")}
            </p>
            <TextField
              label={t("visitNote")}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              hint={t("visitHint")}
            />
            <Button variant="primary" disabled={busy} onClick={verify}>
              {t("verifyButton")}
            </Button>
            <p className="text-xs text-ink-muted">{t("auditNote")}</p>
          </Panel>
          <Panel className="flex flex-col gap-2 p-4 text-sm">
            <h2 className="font-semibold text-ink">{t("facts")}</h2>
            <p>
              {t("capacity")}: <span className="tabular">{c.capacity}</span>
            </p>
            <p>
              {t("hours")}: {c.opening_hours}
            </p>
            <p>
              {reportT("summary.water")}:{" "}
              {c.reports.at(-1)?.wash_available ? reportT("yes") : reportT("no")}
            </p>
            <div>
              <p className="text-xs text-ink-muted">{t("reliability")}</p>
              <ReliabilityMeter score={c.reliability_score} />
            </div>
            <p className="text-xs text-ink-muted">
              {c.ncda_ref ? t("ncdaLinked", { ref: c.ncda_ref }) : t("ncdaNotLinked")}
            </p>
            <SourceChips sources={detail.provenance.sources} />
          </Panel>
        </div>
      </div>
    </>
  );
}
