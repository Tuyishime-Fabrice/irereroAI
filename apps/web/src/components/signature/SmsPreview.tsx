"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

/** A basic phone with the coded SMS on screen and, below it, what the system read from it. */
export function SmsPreview({
  message,
  reply,
  parsed,
}: {
  message: string;
  reply?: ReactNode;
  parsed?: ReactNode;
}) {
  const t = useTranslations("sms");
  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
      <div
        className="w-56 shrink-0 rounded-[22px] border-[3px] border-ink bg-ink p-2"
        role="img"
        aria-label={t("phoneLabel", { message })}
      >
        <div className="rounded-[14px] bg-[#dfe6d8] p-3 font-mono text-[13px] leading-snug text-ink">
          <p className="mb-2 text-[11px] text-ink-muted">{t("to")}: 1234</p>
          <p className="rounded-md bg-surface p-2 break-words">{message || "…"}</p>
          {reply && <p className="mt-2 rounded-md bg-[#c9d8c3] p-2 break-words">{reply}</p>}
        </div>
        <div aria-hidden className="mx-auto mt-2 h-1.5 w-12 rounded-full bg-ink-muted" />
      </div>
      {parsed && <div className="w-full">{parsed}</div>}
    </div>
  );
}
