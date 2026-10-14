"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";

import type { Schemas } from "@/lib/api/client";

type Centre = Schemas["PublicCentre"];

export function countText(
  count: Schemas["PublicCount"] | null | undefined,
  t: (key: string) => string,
) {
  if (!count) return t("notReported");
  if (count.suppressed) return t("fewerThanFive");
  return String(count.value);
}

/** One verified centre in the Find list. Large tap target; all facts in words, not icons alone. */
export function CentreSummary({ centre, selected }: { centre: Centre; selected?: boolean }) {
  const t = useTranslations("find");
  return (
    <Link
      href={`/find/${centre.code}`}
      className={`block rounded-md border bg-surface p-4 hover:border-kivu ${selected ? "border-kivu" : "border-line"}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-ink">{centre.name}</p>
          <p className="text-sm text-ink-muted">
            {t(`type.${centre.type}`)} · {centre.sector_name}
          </p>
        </div>
        {centre.distance_km !== null && (
          <p className="tabular shrink-0 text-sm text-ink">{t("km", { km: centre.distance_km })}</p>
        )}
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink">
        <li>{ages(centre, t)}</li>
        <li>{t(`fee.${centre.fee_band}`)}</li>
        {centre.offers_meals && <li>{t("meals")}</li>}
        <li>
          {t("freePlaces")}: <span className="tabular">{countText(centre.free_places, t)}</span>
        </li>
      </ul>
    </Link>
  );
}

export function ages(centre: Centre, t: (key: string) => string) {
  if (centre.serves_0_2 && centre.serves_3_6) return t("ages.both");
  return centre.serves_0_2 ? t("ages.young") : t("ages.old");
}
