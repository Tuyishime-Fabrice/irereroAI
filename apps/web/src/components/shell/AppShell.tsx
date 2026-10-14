"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Logo } from "@/components/brand/Logo";
import { ZigzagBand } from "@/components/brand/ZigzagBand";
import { SimulatedWatermark } from "@/components/signature/SimulatedWatermark";
import { LoadingState } from "@/components/ui/States";
import type { Schemas } from "@/lib/api/client";
import { weekParts } from "@/lib/format/weeks";

import { DraftTranslationNote } from "./DraftTranslationNote";
import { LocaleToggle } from "./LocaleToggle";
import { NAV } from "./nav";
import { homeFor } from "./roles";
import { ScopeSwitcher } from "./ScopeSwitcher";
import { useSession } from "./SessionProvider";
import { ThemeToggle } from "./ThemeToggle";
import { useWorkspace, WorkspaceProvider } from "./Workspace";

function WeekSelector() {
  const t = useTranslations("shell");
  const months = useTranslations("months");
  const { weeks, week, setWeek, currentWeek } = useWorkspace();
  return (
    <label className="flex items-center gap-2 text-xs text-ink-muted">
      {t("week")}
      <select
        value={week}
        onChange={(e) => setWeek(e.target.value)}
        className="min-h-8 rounded-md border border-line-strong bg-surface px-2 text-sm text-ink"
      >
        {weeks.map((w, i) => {
          const { monthKey, day } = weekParts(w);
          return (
            <option key={w} value={w}>
              {t("weekOption", { n: i + 1, day, month: months(monthKey) })}
              {w === currentWeek ? ` · ${t("thisWeek")}` : ""}
            </option>
          );
        })}
      </select>
    </label>
  );
}

function Shell({ roles, children }: { roles: Schemas["Role"][]; children: ReactNode }) {
  const t = useTranslations("shell");
  const { user, loading, signOut } = useSession();
  const pathname = usePathname();
  const router = useRouter();
  const allowed = user && roles.includes(user.role);

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace(`/sign-in?next=${encodeURIComponent(pathname)}`);
    else if (!roles.includes(user.role)) router.replace(homeFor(user.role));
  }, [loading, user, roles, router, pathname]);

  if (!allowed) return <LoadingState />;
  const nav = NAV[user.role];
  return (
    <div className="min-h-screen">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-surface focus:p-2"
      >
        {t("skip")}
      </a>
      <ZigzagBand className="no-print" />
      <header className="no-print flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface px-4 py-2">
        <div className="flex items-center gap-4">
          <Link href={homeFor(user.role)} aria-label={t("home")}>
            <Logo size={24} />
          </Link>
          <p className="hidden text-sm text-ink-muted sm:block">
            <span className="font-medium text-ink">{t(`role.${user.role}`)}</span>
            {user.scope_name ? ` · ${user.scope_name}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <SimulatedWatermark />
          <DraftTranslationNote />
          {user.role !== "caregiver" && <ScopeSwitcher />}
          {user.role !== "caregiver" && <WeekSelector />}
          <ThemeToggle />
          <LocaleToggle />
          <button
            type="button"
            onClick={async () => {
              await signOut();
              router.push("/");
            }}
            className="min-h-8 rounded-md px-2 text-sm text-kivu underline"
          >
            {t("signOut")}
          </button>
        </div>
      </header>
      <div className="flex flex-col md:flex-row">
        <nav
          aria-label={t("nav")}
          className="no-print border-b border-line bg-surface md:min-h-[calc(100vh-56px)] md:w-56 md:shrink-0 md:border-r md:border-b-0"
        >
          <ul className="flex gap-1 overflow-x-auto p-2 md:flex-col">
            {nav.map((item) => {
              const active =
                item.href === pathname ||
                (item.href !== homeFor(user.role) && pathname.startsWith(item.href));
              return (
                <li key={item.href} className="shrink-0">
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`flex min-h-10 items-center rounded-md px-3 text-sm ${active ? "bg-kivu-tint font-semibold text-kivu" : "text-ink hover:bg-paper"}`}
                  >
                    {t(`navItem.${item.key}`)}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <main id="main" className="min-w-0 flex-1 px-4 py-6 md:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}

/** Signed-in layout: role rail, scope and week in the top bar, simulated-data label. */
export function AppShell({ roles, children }: { roles: Schemas["Role"][]; children: ReactNode }) {
  return (
    <WorkspaceProvider>
      <Shell roles={roles}>{children}</Shell>
    </WorkspaceProvider>
  );
}
