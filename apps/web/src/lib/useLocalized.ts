"use client";

import { useLocale } from "next-intl";

/** Picks the Kinyarwanda or English version of a field pair from API data. */
export function useLocalized() {
  const locale = useLocale();
  return (en: string, rw: string) => (locale === "rw" ? rw : en);
}
