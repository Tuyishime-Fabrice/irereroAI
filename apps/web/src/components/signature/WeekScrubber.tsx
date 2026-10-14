"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { PauseIcon, PlayIcon } from "@/components/ui/icons";
import { weekParts } from "@/lib/format/weeks";

/** Week 1 to week 12: replays how the map and alerts changed as reports arrived. */
export function WeekScrubber({
  weeks,
  value,
  onChange,
}: {
  weeks: string[];
  value: string;
  onChange: (week: string) => void;
}) {
  const t = useTranslations("weeks");
  const months = useTranslations("months");
  const [playing, setPlaying] = useState(false);
  const index = Math.max(0, weeks.indexOf(value));
  const running = playing && index < weeks.length - 1;

  useEffect(() => {
    if (!running) return;
    const timer = setTimeout(() => onChange(weeks[index + 1] as string), 900);
    return () => clearTimeout(timer);
  }, [running, index, weeks, onChange]);

  const { monthKey, day } = weekParts(value);
  return (
    <div className="flex items-center gap-3 rounded-md border border-line bg-surface px-3 py-2">
      <button
        type="button"
        onClick={() => {
          if (!running && index >= weeks.length - 1) onChange(weeks[0] as string);
          setPlaying(!running);
        }}
        className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-line-strong text-kivu"
        aria-label={running ? t("pause") : t("play")}
      >
        {running ? <PauseIcon /> : <PlayIcon />}
      </button>
      <label className="flex flex-1 flex-col gap-1">
        <span className="text-xs text-ink-muted">
          {t("weekOf", { n: index + 1, total: weeks.length, day, month: months(monthKey) })}
        </span>
        <input
          type="range"
          min={0}
          max={weeks.length - 1}
          value={index}
          onChange={(e) => onChange(weeks[Number(e.target.value)] as string)}
          className="w-full accent-[var(--kivu)]"
          aria-valuetext={t("weekOf", {
            n: index + 1,
            total: weeks.length,
            day,
            month: months(monthKey),
          })}
        />
      </label>
    </div>
  );
}
