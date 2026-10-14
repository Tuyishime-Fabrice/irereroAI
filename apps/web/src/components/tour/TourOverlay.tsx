"use client";

import { useTranslations } from "next-intl";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";

import { useSession } from "@/components/shell/SessionProvider";
import { Button } from "@/components/ui/Button";

import { TOUR } from "./steps";
import { readStep, subscribe, writeStep } from "./tourStore";

async function switchTo(role: string): Promise<boolean> {
  const response = await fetch(`/api/demo/login/${role}`, { method: "POST" });
  return response.ok;
}

/** Highlights the element the current step is about, as soon as it appears on the page. */
function useHighlight(target: string | null, pathname: string) {
  useEffect(() => {
    if (!target) return;
    let element: Element | null = null;
    const find = () => {
      const next = document.querySelector(`[data-tour="${target}"]`);
      if (next && next !== element) {
        element?.removeAttribute("data-tour-active");
        element = next;
        element.setAttribute("data-tour-active", "");
        element.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    };
    find();
    const observer = new MutationObserver(find);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => {
      observer.disconnect();
      element?.removeAttribute("data-tour-active");
    };
  }, [target, pathname]);
}

/** The guided judge tour: switches demo account, opens the page and points at what to look at. */
export function TourOverlay() {
  const t = useTranslations("tour");
  const router = useRouter();
  const pathname = usePathname();
  const { user } = useSession();
  const step = useSyncExternalStore(subscribe, readStep, () => null);
  const [busy, setBusy] = useState(false);
  const current = step === null ? null : TOUR[step];
  useHighlight(current?.target ?? null, pathname);

  if (!current || step === null) return null;

  async function go(index: number) {
    const next = TOUR[index];
    if (!next) {
      writeStep(null);
      return;
    }
    writeStep(index);
    if (next.role && next.role !== user?.role) {
      setBusy(true);
      // A full page load avoids racing the old account's role guard during the switch.
      if (await switchTo(next.role)) window.location.assign(next.path);
      else setBusy(false);
      return;
    }
    router.push(next.path);
  }

  return (
    <aside
      aria-label={t("label")}
      aria-live="polite"
      className="no-print fixed right-4 bottom-4 z-50 w-[min(380px,calc(100vw-2rem))] rounded-md border-2 border-ink bg-surface p-4 shadow-[0_2px_0_var(--ink)]"
    >
      <p className="font-mono text-xs font-semibold tracking-wide text-clay uppercase">
        {t("progress", { n: step + 1, total: TOUR.length })}
        {current.role && ` · ${t(`as.${current.role}`)}`}
      </p>
      <h2 className="mt-1 font-display text-lg text-ink">{t(`steps.${current.key}.title`)}</h2>
      <p className="mt-1 text-sm text-ink">{t(`steps.${current.key}.text`)}</p>
      <p className="mt-2 text-xs text-ink-muted">{t(`steps.${current.key}.say`)}</p>
      <div className="mt-3 flex items-center gap-2">
        {step > 0 && (
          <Button onClick={() => go(step - 1)} disabled={busy}>
            {t("back")}
          </Button>
        )}
        <Button variant="primary" onClick={() => go(step + 1)} disabled={busy} className="flex-1">
          {step === TOUR.length - 1 ? t("finish") : t("next")}
        </Button>
        <Button variant="ghost" onClick={() => writeStep(null)}>
          {t("exit")}
        </Button>
      </div>
    </aside>
  );
}
