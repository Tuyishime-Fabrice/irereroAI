"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";

import { useProvenance } from "@/components/shell/ProvenanceProvider";
import { useWorkspace } from "@/components/shell/Workspace";
import { AlertRow } from "@/components/signature/AlertRow";
import { ReliabilityMeter } from "@/components/signature/ReliabilityMeter";
import { SourceChips } from "@/components/signature/SourceChip";
import { TrendChart } from "@/components/signature/TrendChart";
import { Button } from "@/components/ui/Button";
import { CheckIcon, CloudOffIcon } from "@/components/ui/icons";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { useOutbox } from "@/lib/offline/useOutbox";

import { useMyCentre } from "./useMyCentre";

export function CaregiverHome() {
  const t = useTranslations("caregiver");
  const { data, loading, error, reload } = useMyCentre();
  const { currentWeek, weeks } = useWorkspace();
  const outbox = useOutbox();
  useProvenance(data?.provenance);
  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState onRetry={reload} />;
  const centre = data.data;
  const queued = outbox.items.find((item) => item.body.week_start === currentWeek);
  const reported =
    centre.reported_this_week || centre.reports.some((r) => r.week_start === currentWeek);
  const trend = weeks.map((week, i) => {
    const r = centre.reports.find((report) => report.week_start === week);
    return {
      label: `${i + 1}`,
      enrolled: r
        ? r.enrolled_0_2_female + r.enrolled_0_2_male + r.enrolled_3_6_female + r.enrolled_3_6_male
        : null,
      attendance: r?.avg_daily_attendance ?? null,
      meals: r?.days_meal_served ?? null,
      water: r ? (r.wash_available ? 1 : 0) : null,
    };
  });

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-5">
      <div>
        <p className="text-sm text-ink-muted">{centre.sector_name}</p>
        <h1 className="font-display text-3xl text-ink">{centre.name}</h1>
      </div>

      <Panel className={`p-5 ${reported ? "border-success" : "border-clay"} border-l-4`}>
        {reported ? (
          <p className="flex items-center gap-2 text-lg font-semibold text-success">
            <CheckIcon /> {t("reportedThisWeek")}
          </p>
        ) : queued ? (
          <div className="flex flex-col gap-2">
            <p className="flex items-center gap-2 text-lg font-semibold text-ochre-text">
              <CloudOffIcon />{" "}
              {queued.status === "needs_attention" ? t("queuedProblem") : t("queuedWaiting")}
            </p>
            {outbox.online && queued.status !== "needs_attention" && (
              <Button onClick={() => outbox.sync()} className="self-start">
                {t("sendNow")}
              </Button>
            )}
            {queued.status === "needs_attention" && (
              <Button
                variant="danger"
                className="self-start"
                onClick={() => outbox.discard(queued.id)}
              >
                {t("discardQueued")}
              </Button>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-lg font-semibold text-ink">{t("notYet")}</p>
            <p className="text-sm text-ink-muted">{t("takesThree")}</p>
            <Link
              href="/caregiver/report"
              className="inline-flex min-h-12 items-center justify-center self-start rounded-md bg-kivu px-6 text-base font-medium text-white"
            >
              {t("startReport")}
            </Link>
          </div>
        )}
        {outbox.lastSent > 0 && (
          <p className="mt-2 text-sm text-success">{t("syncedNow", { n: outbox.lastSent })}</p>
        )}
        {!outbox.online && <p className="mt-2 text-sm text-ink-muted">{t("offlineNote")}</p>}
      </Panel>

      {centre.alerts.filter((a) => a.status !== "resolved").length > 0 && (
        <Panel>
          <PanelHeader title={t("alertsTitle")} />
          <div className="flex flex-col gap-2 p-3">
            {centre.alerts
              .filter((a) => a.status !== "resolved")
              .map((alert) => (
                <AlertRow key={alert.id} alert={alert} />
              ))}
            <p className="px-1 text-sm text-ink-muted">{t("alertsNote")}</p>
          </div>
        </Panel>
      )}

      <Panel>
        <PanelHeader title={t("trendsTitle")} />
        <div className="grid gap-6 p-4 md:grid-cols-2">
          <TrendChart
            title={t("trendChildren")}
            data={trend}
            series={[
              { key: "enrolled", label: t("enrolled"), colour: "var(--ink)" },
              { key: "attendance", label: t("attendance"), colour: "var(--kivu)" },
            ]}
          />
          <TrendChart
            title={t("trendServices")}
            data={trend}
            series={[
              { key: "meals", label: t("mealDays"), colour: "var(--clay)" },
              { key: "water", label: t("water"), colour: "var(--kivu)", dashed: true },
            ]}
          />
        </div>
        <p className="px-4 pb-4 text-xs text-ink-muted">{t("trendNote")}</p>
      </Panel>

      <div className="grid gap-5 md:grid-cols-2">
        <Panel className="flex flex-col gap-3 p-5">
          <h2 className="font-semibold text-ink">{t("statusTitle")}</h2>
          <p className="text-sm text-ink">
            {centre.verified
              ? t("verified", { date: centre.verified_at?.slice(0, 10) ?? "" })
              : t("notVerified")}
          </p>
          <div>
            <p className="text-xs text-ink-muted">{t("reliability")}</p>
            <ReliabilityMeter score={centre.reliability_score} />
          </div>
          <SourceChips sources={data.provenance.sources} />
        </Panel>
        <Panel className="flex flex-col gap-2 p-5">
          <h2 className="font-semibold text-ink">{t("givesBackTitle")}</h2>
          <ul className="flex flex-col gap-1 text-sm text-ink">
            <li>· {t("givesBack.parents")}</li>
            <li>· {t("givesBack.officer")}</li>
            <li>· {t("givesBack.plan")}</li>
          </ul>
        </Panel>
      </div>
    </div>
  );
}
