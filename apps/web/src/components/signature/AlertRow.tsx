"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { AlertIcon } from "@/components/ui/icons";
import type { Schemas } from "@/lib/api/client";
import { useLocalized } from "@/lib/useLocalized";

type Alert = Schemas["AlertOut"];

const SEVERITY = {
  critical: "border-l-danger text-danger",
  warning: "border-l-ochre text-ochre-text",
  info: "border-l-kivu text-kivu",
} as const;

/** Centre, signal, reason in plain words, age, status and an action slot. */
export function AlertRow({ alert, action }: { alert: Alert; action?: ReactNode }) {
  const t = useTranslations("alerts");
  const pick = useLocalized();
  return (
    <article
      className={`grid gap-2 border-l-4 bg-surface px-4 py-3 sm:grid-cols-[1fr_auto] ${SEVERITY[alert.severity]}`}
      aria-label={`${t(`severity.${alert.severity}`)}: ${alert.centre_name}`}
    >
      <div className="flex flex-col gap-1">
        <p className="flex flex-wrap items-center gap-2 text-sm font-semibold">
          <AlertIcon />
          <span>{t(`severity.${alert.severity}`)}</span>
          <span className="text-ink">· {t(`kind.${alert.kind}`)}</span>
          <span className="font-normal text-ink-muted">· {alert.centre_name}</span>
        </p>
        <p className="text-sm text-ink">{pick(alert.reason_en, alert.reason_rw)}</p>
        <p className="text-xs text-ink-muted">
          {t("age", { weeks: alert.age_weeks })} · {t(`status.${alert.status}`)}
          {alert.assigned_name && ` · ${t("assignedTo", { name: alert.assigned_name })}`}
        </p>
      </div>
      {action && <div className="flex items-start gap-2">{action}</div>}
    </article>
  );
}
