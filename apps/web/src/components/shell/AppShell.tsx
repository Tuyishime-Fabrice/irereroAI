"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Logo } from "@/components/brand/Logo";
import { ZigzagBand } from "@/components/brand/ZigzagBand";
import { SimulatedWatermark } from "@/components/signature/SimulatedWatermark";
import { LoadingState } from "@/components/ui/States";

import { DraftTranslationNote } from "./DraftTranslationNote";
import { LocaleToggle } from "./LocaleToggle";
import { HOME, NAV } from "./nav";
import { useSession } from "./SessionProvider";
import { ThemeToggle } from "./ThemeToggle";
import { WorkspaceProvider } from "./Workspace";

function Shell({ children }: { children: ReactNode }) {
  const t = useTranslations("shell");
  const { user, loading, signOut } = useSession();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace(`/sign-in?next=${encodeURIComponent(pathname)}`);
  }, [loading, user, router, pathname]);

  if (!user) return <LoadingState />;
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
          <Link href={HOME} aria-label={t("home")}>
            <Logo size={24} />
          </Link>
          <p className="hidden text-sm text-ink-muted sm:block">
            <span className="font-medium text-ink">{t("role")}</span> · {user.district_name}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <SimulatedWatermark />
          <DraftTranslationNote />
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
            {NAV.map((item) => {
              const active =
                item.href === pathname || (item.href !== HOME && pathname.startsWith(item.href));
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

/** Signed-in layout for the planner: the rail, the district, and the simulated-data label. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <WorkspaceProvider>
      <Shell>{children}</Shell>
    </WorkspaceProvider>
  );
}
