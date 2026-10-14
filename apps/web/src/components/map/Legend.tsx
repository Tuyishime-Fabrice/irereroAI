"use client";

import { useTranslations } from "next-intl";

import { NEED_COLOURS } from "./classes";

export function Legend({
  title,
  labels,
  showHatch,
}: {
  title: string;
  labels: string[];
  showHatch: boolean;
}) {
  const t = useTranslations("map");
  return (
    <div className="flex flex-col gap-2 rounded-md border border-line bg-surface p-3 text-xs text-ink">
      <p className="font-semibold">{title}</p>
      <ol className="flex flex-col gap-1">
        {NEED_COLOURS.map((colour, i) => (
          <li key={colour} className="flex items-center gap-2">
            <span
              aria-hidden
              className="h-3 w-5 rounded-[2px] border border-line"
              style={{ background: colour }}
            />
            <span className="tabular">{labels[i] ?? ""}</span>
          </li>
        ))}
      </ol>
      {showHatch && (
        <p className="flex items-center gap-2 border-t border-line pt-2">
          <svg aria-hidden width="20" height="12" viewBox="0 0 20 12">
            <rect width="20" height="12" fill="#EBC28E" />
            <path
              d="M0 9 3 3 6 9 9 3 12 9 15 3 18 9"
              fill="none"
              stroke="#1E1B18"
              strokeWidth="1.2"
            />
          </svg>
          {t("hatchLegend")}
        </p>
      )}
    </div>
  );
}
