"use client";

import { useLocale, useTranslations } from "next-intl";

/** Kinyarwanda text is a draft until a reviewer signs it off (docs/i18n-review.md). */
export function DraftTranslationNote() {
  const locale = useLocale();
  const t = useTranslations("common");
  if (locale !== "rw") return null;
  return (
    <span className="inline-flex items-center rounded-sm border border-ochre px-1.5 py-0.5 text-[11px] text-ochre-text">
      {t("draftTranslation")}
    </span>
  );
}
