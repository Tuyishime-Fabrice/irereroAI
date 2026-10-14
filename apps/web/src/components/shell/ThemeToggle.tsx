"use client";

import { useTranslations } from "next-intl";
import { useSyncExternalStore } from "react";

const KEY = "irerero_theme";

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

const isProjector = () => document.documentElement.dataset.theme === "projector";

/** High-contrast "projector" theme for live presentations. */
export function ThemeToggle() {
  const t = useTranslations("common");
  const projector = useSyncExternalStore(subscribe, isProjector, () => false);
  return (
    <button
      type="button"
      aria-pressed={projector}
      onClick={() => {
        if (projector) delete document.documentElement.dataset.theme;
        else document.documentElement.dataset.theme = "projector";
        try {
          localStorage.setItem(KEY, projector ? "light" : "projector");
        } catch {
          // Storage can be unavailable in private mode; the toggle still works for this page.
        }
      }}
      className="min-h-8 rounded-md border border-line-strong bg-surface px-2.5 text-xs font-semibold text-ink"
    >
      {t("projector")}
    </button>
  );
}
