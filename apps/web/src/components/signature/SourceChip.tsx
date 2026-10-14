"use client";

import { useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState } from "react";

import type { SourceValue } from "@/lib/api/client";

const ORIGIN_STYLE = {
  official: "border-ink text-ink",
  public: "border-kivu text-kivu",
  partner: "border-kivu text-kivu",
  simulated: "border-clay text-clay",
} as const;

/** Source and year; tap or hover reveals the table, origin and what that origin means. */
export function SourceChip({ source }: { source: SourceValue }) {
  const t = useTranslations("provenance");
  const [open, setOpen] = useState(false);
  const id = useId();
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent | MouseEvent) => {
      if (
        event instanceof KeyboardEvent
          ? event.key === "Escape"
          : !ref.current?.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", close);
    document.addEventListener("mousedown", close);
    return () => {
      document.removeEventListener("keydown", close);
      document.removeEventListener("mousedown", close);
    };
  }, [open]);

  const label = source.source.split(";")[0]?.split(" (")[0] ?? source.source;
  return (
    <span ref={ref} className="relative inline-block" onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((value) => !value)}
        onMouseEnter={() => setOpen(true)}
        className={`inline-flex max-w-64 items-center gap-1 truncate rounded-sm border bg-surface px-1.5 py-0.5 text-xs ${ORIGIN_STYLE[source.origin]}`}
      >
        <span className="truncate">{label}</span>
        <span className="tabular">· {source.reference_year}</span>
      </button>
      {open && (
        <span
          id={id}
          role="tooltip"
          className="absolute top-full left-0 z-30 mt-1 w-72 rounded-md border border-line bg-surface p-3 text-xs text-ink shadow-[0_1px_2px_rgba(30,27,24,0.12)]"
        >
          <span className="block font-medium">{source.source}</span>
          <span className="mt-1 block text-ink-muted">
            {t("table")}: <span className="tabular">{source.table}</span> · {t("year")}:{" "}
            <span className="tabular">{source.reference_year}</span>
          </span>
          <span className="mt-2 block">
            <strong>{t(`origin.${source.origin}`)}</strong> — {t(`originExplain.${source.origin}`)}
          </span>
        </span>
      )}
    </span>
  );
}

export function SourceChips({ sources }: { sources: SourceValue[] }) {
  const unique = sources.filter(
    (s, i) => sources.findIndex((o) => o.source === s.source && o.table === s.table) === i,
  );
  return (
    <span className="flex flex-wrap gap-1">
      {unique.map((s) => (
        <SourceChip key={`${s.table}-${s.source}-${s.reference_year}`} source={s} />
      ))}
    </span>
  );
}
