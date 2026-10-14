"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useState } from "react";

import { useProvenance } from "@/components/shell/ProvenanceProvider";
import { AlertRow } from "@/components/signature/AlertRow";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel } from "@/components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";

import { useAlerts, useSectorCode } from "./useSector";

const FILTERS = ["active", "open", "acknowledged", "resolved"] as const;

export function AlertsQueue() {
  const t = useTranslations("sector");
  const alerts = useAlerts(useSectorCode());
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("active");
  useProvenance(alerts.data?.provenance);
  if (alerts.loading) return <LoadingState />;
  if (alerts.error || !alerts.data) return <ErrorState onRetry={alerts.reload} />;
  const shown = alerts.data.data.filter((a) =>
    filter === "active" ? a.status !== "resolved" : a.status === filter,
  );
  return (
    <>
      <PageTitle title={t("alertsTitle")} lead={t("alertsLead")} />
      <div role="group" aria-label={t("filter")} className="mb-4 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            aria-pressed={filter === f}
            onClick={() => setFilter(f)}
            className={`min-h-9 rounded-md border px-3 text-sm ${filter === f ? "border-kivu bg-kivu-tint text-kivu" : "border-line-strong bg-surface text-ink"}`}
          >
            {t(`filters.${f}`)}
          </button>
        ))}
      </div>
      <Panel data-tour="alert-list">
        {shown.length === 0 ? (
          <EmptyState title={t("noAlerts")} />
        ) : (
          <div className="flex flex-col gap-2 p-3">
            {shown.map((alert) => (
              <AlertRow
                key={alert.id}
                alert={alert}
                action={
                  <Link
                    href={`/sector/alerts/${alert.id}`}
                    className="inline-flex min-h-10 items-center rounded-md border border-line-strong px-3 text-sm text-ink"
                  >
                    {t("open")}
                  </Link>
                }
              />
            ))}
          </div>
        )}
      </Panel>
    </>
  );
}
