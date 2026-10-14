"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";

import { Logo } from "@/components/brand/Logo";
import { ZigzagBand } from "@/components/brand/ZigzagBand";
import { SimulatedWatermark } from "@/components/signature/SimulatedWatermark";

import { DraftTranslationNote } from "./DraftTranslationNote";
import { LocaleToggle } from "./LocaleToggle";
import { homeFor } from "./roles";
import { useSession } from "./SessionProvider";
import { ThemeToggle } from "./ThemeToggle";

export function PublicHeader() {
  const t = useTranslations("public");
  const { user } = useSession();
  return (
    <header className="no-print">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-surface focus:p-2"
      >
        {t("skip")}
      </a>
      <ZigzagBand />
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link href="/" aria-label={t("home")}>
          <Logo />
        </Link>
        <nav aria-label={t("navLabel")} className="flex flex-wrap items-center gap-4 text-sm">
          <Link href="/find" className="text-ink hover:text-kivu">
            {t("nav.find")}
          </Link>
          <Link href="/methodology" className="text-ink hover:text-kivu">
            {t("nav.methodology")}
          </Link>
          <Link
            href={user ? (user.role === "parent" ? "/account" : homeFor(user.role)) : "/sign-in"}
            className="rounded-md border border-kivu px-3 py-1.5 font-medium text-kivu hover:bg-kivu-tint"
          >
            {user ? t("nav.myWork") : t("nav.signIn")}
          </Link>
        </nav>
        <div className="flex items-center gap-2">
          <SimulatedWatermark />
          <DraftTranslationNote />
          <ThemeToggle />
          <LocaleToggle />
        </div>
      </div>
    </header>
  );
}
