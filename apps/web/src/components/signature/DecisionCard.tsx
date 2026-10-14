"use client";

import { useTranslations } from "next-intl";
import { useId, useState } from "react";

import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import {
  BuildIcon,
  CheckIcon,
  CloseIcon,
  EditIcon,
  QuestionIcon,
  SupportIcon,
  UpgradeIcon,
} from "@/components/ui/icons";
import type { Schemas } from "@/lib/api/client";
import { formatNumber, formatRange, formatRwf } from "@/lib/format/numbers";
import { useLocalized } from "@/lib/useLocalized";

import { DriverBars } from "./DriverBars";
import { RangeBar } from "./RangeBar";
import { SourceChips } from "./SourceChip";

type Recommendation = Schemas["RecommendationOut"];
type Decision = Schemas["DecisionIn"];
const REASONS = [
  "no_land",
  "already_funded",
  "access_problem",
  "community_objection",
  "other",
] as const;
const ACTION_ICON = { build: BuildIcon, upgrade: UpgradeIcon, support: SupportIcon };
const STATUS_STYLE = {
  proposed: "border-line",
  approved: "border-kivu",
  edited: "border-ochre",
  rejected: "border-danger opacity-80",
} as const;

/** One suggestion: what, where, what it would change, why, from which data, and the decision. */
export function DecisionCard({
  recommendation: rec,
  maxReached,
  canDecide,
  onDecide,
  onAsk,
}: {
  recommendation: Recommendation;
  maxReached: number;
  canDecide: boolean;
  onDecide: (decision: Decision) => Promise<void>;
  onAsk?: () => void;
}) {
  const t = useTranslations("decision");
  const pick = useLocalized();
  const [mode, setMode] = useState<"idle" | "reject" | "edit">("idle");
  const [reason, setReason] = useState<(typeof REASONS)[number] | "">("");
  const [note, setNote] = useState("");
  const [cost, setCost] = useState(String(Math.round(rec.cost.estimate)));
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const headingId = useId();
  const Icon = ACTION_ICON[rec.action];
  const decided = rec.status !== "proposed";
  const last = rec.decisions.at(-1);

  async function submit(decision: Decision) {
    setBusy(true);
    setProblem(null);
    try {
      await onDecide(decision);
      setMode("idle");
    } catch {
      setProblem(t("failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <article
      aria-labelledby={headingId}
      className={`flex flex-col gap-4 rounded-md border bg-surface p-4 ${STATUS_STYLE[rec.status]} border-l-4`}
    >
      <header className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span
            className="font-display text-2xl leading-none text-ink-muted tabular"
            aria-label={t("rank", { rank: rec.rank })}
          >
            {rec.rank}
          </span>
          <div>
            <p className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-clay uppercase">
              <Icon /> {t(`action.${rec.action}`)}
            </p>
            <h3 id={headingId} className="text-base font-semibold text-ink">
              {rec.site_name}
            </h3>
            <p className="text-sm text-ink-muted">{rec.sector_name}</p>
          </div>
        </div>
        <span className="rounded-sm border border-line px-2 py-0.5 text-xs text-ink-muted">
          {t("suggestion")} · {t(`status.${rec.status}`)}
        </span>
      </header>

      {rec.action === "support" ? (
        <p className="text-sm text-ink">
          {t("supported", { n: formatNumber(rec.children_supported) })}
        </p>
      ) : (
        <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <dt className="text-xs text-ink-muted">{t("reached")}</dt>
            <dd>
              <RangeBar value={rec.children_reached} max={maxReached} label={t("reached")} />
            </dd>
          </div>
          <div>
            <dt className="text-xs text-ink-muted">{t("highRisk")}</dt>
            <dd className="tabular text-sm">{formatRange(rec.high_risk_children_reached)}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-muted">{t("mothers")}</dt>
            <dd className="tabular text-sm">{formatRange(rec.mothers_under3_reached)}</dd>
          </div>
        </dl>
      )}

      <div className="grid gap-4 sm:grid-cols-[1fr_auto]">
        <div>
          <p className="mb-1.5 text-xs text-ink-muted">{t("why")}</p>
          <DriverBars drivers={rec.drivers} />
        </div>
        <div className="text-right">
          <p className="text-xs text-ink-muted">{t("cost")}</p>
          <p className="tabular text-sm">{formatRwf(rec.cost.estimate, true)}</p>
          <p className="tabular text-xs text-ink-muted">
            {formatRwf(rec.cost.low, true)}–{formatRwf(rec.cost.high, true)}
          </p>
        </div>
      </div>

      <details className="text-sm">
        <summary className="cursor-pointer text-kivu">{t("explain")}</summary>
        <p className="mt-2 text-ink">{pick(rec.explanation_en, rec.explanation_rw)}</p>
      </details>

      <SourceChips sources={rec.sources} />

      {last && (
        <p className="text-xs text-ink-muted">
          {t(`verdict.${last.verdict}`)} · {last.user_name}
          {last.reason_code && ` · ${t(`reason.${last.reason_code}`)}`}
          {last.reason_text && ` · “${last.reason_text}”`}
        </p>
      )}

      {canDecide && !decided && mode === "idle" && (
        <div className="flex flex-wrap gap-2 border-t border-line pt-3">
          <Button variant="primary" disabled={busy} onClick={() => submit({ verdict: "approve" })}>
            <CheckIcon /> {t("approve")}
          </Button>
          <Button disabled={busy} onClick={() => setMode("edit")}>
            <EditIcon /> {t("edit")}
          </Button>
          <Button variant="danger" disabled={busy} onClick={() => setMode("reject")}>
            <CloseIcon /> {t("reject")}
          </Button>
          {onAsk && (
            <Button variant="ghost" onClick={onAsk} className="ml-auto">
              <QuestionIcon /> {t("ask")}
            </Button>
          )}
        </div>
      )}
      {!(canDecide && !decided && mode === "idle") && onAsk && mode === "idle" && (
        <Button variant="ghost" onClick={onAsk} className="self-start">
          <QuestionIcon /> {t("ask")}
        </Button>
      )}

      {mode === "reject" && (
        <form
          className="flex flex-col gap-3 border-t border-line pt-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (!reason) return;
            void submit({ verdict: "reject", reason_code: reason, reason_text: note || null });
          }}
        >
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink">{t("rejectWhy")}</legend>
            <div className="grid gap-1 sm:grid-cols-2">
              {REASONS.map((code) => (
                <label key={code} className="flex min-h-10 items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name={`reason-${rec.id}`}
                    value={code}
                    checked={reason === code}
                    onChange={() => setReason(code)}
                    className="h-4 w-4 accent-[var(--danger)]"
                  />
                  {t(`reason.${code}`)}
                </label>
              ))}
            </div>
          </fieldset>
          <TextField
            label={t("note")}
            value={note}
            required={reason === "other"}
            onChange={(e) => setNote(e.target.value)}
            hint={reason === "other" ? t("noteRequired") : t("noteOptional")}
          />
          <p className="text-xs text-ink-muted">{t("rejectEffect")}</p>
          <div className="flex gap-2">
            <Button
              type="submit"
              variant="danger"
              disabled={busy || !reason || (reason === "other" && !note.trim())}
            >
              {t("confirmReject")}
            </Button>
            <Button onClick={() => setMode("idle")}>{t("cancel")}</Button>
          </div>
        </form>
      )}

      {mode === "edit" && (
        <form
          className="flex flex-col gap-3 border-t border-line pt-3"
          onSubmit={(e) => {
            e.preventDefault();
            void submit({
              verdict: "edit",
              edits: { cost_rwf: Number(cost) },
              reason_text: note || null,
            });
          }}
        >
          <TextField
            label={t("editCost")}
            inputMode="numeric"
            value={cost}
            onChange={(e) => setCost(e.target.value.replace(/\D/g, ""))}
          />
          <TextField
            label={t("note")}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            hint={t("noteOptional")}
          />
          <div className="flex gap-2">
            <Button type="submit" variant="primary" disabled={busy || !Number(cost)}>
              {t("saveEdit")}
            </Button>
            <Button onClick={() => setMode("idle")}>{t("cancel")}</Button>
          </div>
        </form>
      )}
      {problem && (
        <p role="alert" className="text-sm text-danger">
          {problem}
        </p>
      )}
    </article>
  );
}
