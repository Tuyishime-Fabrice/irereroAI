"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";

import { LOCALE_COOKIE, locales } from "@/i18n/config";

export function LocaleToggle() {
  const locale = useLocale();
  const router = useRouter();
  const t = useTranslations("common");
  return (
    <div
      role="group"
      aria-label={t("language")}
      className="inline-flex overflow-hidden rounded-md border border-line-strong text-xs font-semibold"
    >
      {locales.map((code) => (
        <button
          key={code}
          type="button"
          aria-pressed={locale === code}
          lang={code}
          onClick={() => {
            document.cookie = `${LOCALE_COOKIE}=${code}; path=/; max-age=31536000; samesite=lax`;
            router.refresh();
          }}
          className={`min-h-8 px-2.5 uppercase ${locale === code ? "bg-ink text-white" : "bg-surface text-ink"}`}
        >
          {code}
        </button>
      ))}
    </div>
  );
}
