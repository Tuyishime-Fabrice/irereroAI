"use client";

import { useTranslations } from "next-intl";

import type { DriverValue } from "@/lib/api/client";
import { useLocalized } from "@/lib/useLocalized";

/** The top reasons as small bars with plain-language labels. */
export function DriverBars({ drivers }: { drivers: DriverValue[] }) {
  const t = useTranslations("drivers");
  const pick = useLocalized();
  if (!drivers.length) return <p className="text-sm text-ink-muted">{t("none")}</p>;
  // Bars are relative to the strongest reason, so the first one always reads as "main".
  const strongest = Math.max(...drivers.map((d) => d.contribution), 0.01);
  return (
    <ul className="flex flex-col gap-1.5" aria-label={t("title")}>
      {drivers.slice(0, 3).map((driver) => (
        <li key={driver.feature} className="grid grid-cols-[1fr_72px] items-center gap-3 text-sm">
          <span className="text-ink">{pick(driver.label_en, driver.label_rw)}</span>
          <span aria-hidden className="h-2 rounded-sm bg-line">
            <span
              className="block h-full rounded-sm bg-clay"
              style={{ width: `${Math.round((driver.contribution / strongest) * 100)}%` }}
            />
          </span>
        </li>
      ))}
    </ul>
  );
}
