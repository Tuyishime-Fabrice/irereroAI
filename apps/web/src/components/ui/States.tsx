"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { Spiral } from "@/components/brand/Spiral";

import { Button } from "./Button";

export function EmptyState({ title, children }: { title: ReactNode; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-10 text-center">
      <Spiral />
      <p className="font-medium text-ink">{title}</p>
      {children && <div className="max-w-md text-sm text-ink-muted">{children}</div>}
    </div>
  );
}

export function LoadingState({ label }: { label?: string }) {
  const t = useTranslations("common");
  return (
    <div role="status" className="flex items-center gap-3 px-4 py-8 text-ink-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-kivu" />
      {label ?? t("loading")}
    </div>
  );
}

export function ErrorState({ onRetry, message }: { onRetry?: () => void; message?: string }) {
  const t = useTranslations("common");
  return (
    <div role="alert" className="flex flex-col items-start gap-3 px-4 py-6">
      <p className="font-medium text-danger">{message ?? t("error")}</p>
      {onRetry && <Button onClick={onRetry}>{t("retry")}</Button>}
    </div>
  );
}
