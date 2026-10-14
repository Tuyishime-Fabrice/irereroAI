"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useState } from "react";

import { AssistantDrawer, type AssistantSubject } from "@/components/assistant/AssistantDrawer";
import { useProvenance } from "@/components/shell/ProvenanceProvider";
import { AlertRow } from "@/components/signature/AlertRow";
import { SourceChips } from "@/components/signature/SourceChip";
import { TrendChart } from "@/components/signature/TrendChart";
import { Button } from "@/components/ui/Button";
import { SelectField, TextField } from "@/components/ui/Field";
import { QuestionIcon } from "@/components/ui/icons";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { api, type Schemas } from "@/lib/api/client";
import { useApi } from "@/lib/useApi";

type Detail = Schemas["Envelope_AlertDetail_"];

export function AlertDetail({ id }: { id: string }) {
  const t = useTranslations("sector");
  const reportT = useTranslations("report");
  const [override, setOverride] = useState<Detail | null>(null);
  const loaded = useApi(`alert:${id}`, async () => {
    const { data } = await api.GET("/alerts/{alert_id}", { params: { path: { alert_id: id } } });
    return data ?? null;
  });
  const detail = override ?? loaded.data;
  const officers = useApi(detail ? `officers:${detail.data.centre_code}` : null, async () => {
    if (!detail) return null;
    const { data } = await api.GET("/officers", {
      params: { query: { centre_code: detail.data.centre_code } },
    });
    return data ?? null;
  });
  const [note, setNote] = useState("");
  const [assignee, setAssignee] = useState("");
  const [busy, setBusy] = useState(false);
  const [asking, setAsking] = useState<AssistantSubject | null>(null);
  useProvenance(detail?.provenance);

  if (loaded.loading && !detail) return <LoadingState />;
  if (!detail) return <ErrorState onRetry={loaded.reload} />;
  const alert = detail.data;

  async function act(path: "acknowledge" | "assign" | "resolve") {
    setBusy(true);
    const params = { path: { alert_id: id } };
    const result =
      path === "acknowledge"
        ? await api.POST("/alerts/{alert_id}/acknowledge", { params })
        : path === "assign"
          ? await api.POST("/alerts/{alert_id}/assign", { params, body: { user_id: assignee } })
          : await api.POST("/alerts/{alert_id}/resolve", { params, body: { note } });
    if (result.data) setOverride(result.data);
    setBusy(false);
  }

  const trend = alert.reports.map((r, i) => ({
    label: `${i + 1}`,
    enrolled:
      r.enrolled_0_2_female + r.enrolled_0_2_male + r.enrolled_3_6_female + r.enrolled_3_6_male,
    attendance: r.avg_daily_attendance,
    capacity: alert.capacity,
  }));

  return (
    <>
      <Link href="/sector/alerts" className="text-sm text-kivu underline">
        ← {t("alertsTitle")}
      </Link>
      <div className="mt-3">
        <PageTitle
          title={alert.centre_name}
          lead={t(`kindLead.${alert.kind}`)}
          actions={
            <Button
              variant="ghost"
              onClick={() => setAsking({ kind: "alert", id: alert.id, title: alert.centre_name })}
            >
              <QuestionIcon /> {t("why")}
            </Button>
          }
        />
      </div>
      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <div className="flex flex-col gap-6">
          <AlertRow alert={alert} />
          <Panel>
            <PanelHeader title={t("trend")} />
            <div className="p-4">
              <TrendChart
                title={t("trend")}
                data={trend}
                series={[
                  { key: "enrolled", label: t("enrolled"), colour: "var(--ink)" },
                  { key: "attendance", label: t("attendance"), colour: "var(--kivu)" },
                  { key: "capacity", label: t("capacity"), colour: "var(--clay)", dashed: true },
                ]}
              />
            </div>
          </Panel>
          <Panel>
            <PanelHeader title={t("recentReports")} />
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-ink-muted">
                  <tr>
                    <th scope="col" className="px-4 py-2">
                      {t("weekCol")}
                    </th>
                    <th scope="col" className="px-4 py-2">
                      {t("attendance")}
                    </th>
                    <th scope="col" className="px-4 py-2">
                      {reportT("summary.water")}
                    </th>
                    <th scope="col" className="px-4 py-2">
                      {reportT("summary.problem")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {alert.reports.slice(-6).map((r) => (
                    <tr key={r.week_start} className="border-t border-line">
                      <td className="tabular px-4 py-2">{r.week_start}</td>
                      <td className="tabular px-4 py-2">{r.avg_daily_attendance}</td>
                      <td className="px-4 py-2">
                        {r.wash_available ? (
                          reportT("yes")
                        ) : (
                          <span className="text-danger">{reportT("no")}</span>
                        )}
                      </td>
                      <td className="px-4 py-2">{reportT(`problems.${r.main_problem}`)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
          <SourceChips sources={detail.provenance.sources} />
        </div>
        <Panel className="flex flex-col gap-4 self-start p-4">
          <h2 className="font-semibold text-ink">{t("followUp")}</h2>
          {alert.status === "resolved" ? (
            <p className="text-sm text-success">
              {t("resolvedWith", { note: alert.resolution_note ?? "" })}
            </p>
          ) : (
            <>
              {alert.status === "open" && (
                <Button variant="primary" disabled={busy} onClick={() => act("acknowledge")}>
                  {t("acknowledge")}
                </Button>
              )}
              <div className="flex flex-col gap-2">
                <SelectField
                  label={t("assign")}
                  value={assignee}
                  onChange={(e) => setAssignee(e.target.value)}
                >
                  <option value="">{t("chooseOfficer")}</option>
                  {officers.data?.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.display_name}
                    </option>
                  ))}
                </SelectField>
                <Button disabled={busy || !assignee} onClick={() => act("assign")}>
                  {t("assignButton")}
                </Button>
              </div>
              <div className="flex flex-col gap-2 border-t border-line pt-4">
                <TextField
                  label={t("resolveNote")}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  hint={t("resolveHint")}
                />
                <Button
                  variant="primary"
                  disabled={busy || !note.trim()}
                  onClick={() => act("resolve")}
                >
                  {t("resolve")}
                </Button>
              </div>
            </>
          )}
          <p className="text-xs text-ink-muted">{t("auditNote")}</p>
        </Panel>
      </div>
      <AssistantDrawer subject={asking} onClose={() => setAsking(null)} />
    </>
  );
}
