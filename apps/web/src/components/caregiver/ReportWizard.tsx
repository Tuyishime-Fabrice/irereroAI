"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useMemo, useState } from "react";

import { useProvenance } from "@/components/shell/ProvenanceProvider";
import { useWorkspace } from "@/components/shell/Workspace";
import { Button } from "@/components/ui/Button";
import { CloudOffIcon } from "@/components/ui/icons";
import { Panel } from "@/components/ui/Panel";
import { ErrorState, LoadingState } from "@/components/ui/States";
import type { Schemas } from "@/lib/api/client";
import { weekParts } from "@/lib/format/weeks";
import { send, type ReportBody } from "@/lib/offline/outbox";
import { useOutbox } from "@/lib/offline/useOutbox";

import { NumberStepper } from "./NumberStepper";
import { enrolled, PROBLEMS, stepProblem, STEPS } from "./reportSteps";
import { useMyCentre } from "./useMyCentre";

type Outcome = "sent" | "queued" | "duplicate";
const COUNT_KEYS = [
  "enrolled_0_2_female",
  "enrolled_0_2_male",
  "enrolled_3_6_female",
  "enrolled_3_6_male",
  "avg_daily_attendance",
  "waiting_list",
  "caregivers_present",
  "days_open",
  "days_meal_served",
  "referrals_growth_monitoring",
  "children_with_disability",
] as const;

function startingPoint(centre: Schemas["CentreDetail"], week: string): ReportBody {
  const last = centre.reports.at(-1);
  const counts = Object.fromEntries(COUNT_KEYS.map((k) => [k, last ? last[k] : 0])) as Record<
    (typeof COUNT_KEYS)[number],
    number
  >;
  return {
    centre_code: centre.code,
    week_start: week,
    ...counts,
    wash_available: last?.wash_available ?? true,
    main_problem: "none",
    channel: "web",
    confirmed: false,
  };
}

export function ReportWizard() {
  const { data: centre, loading, error, reload } = useMyCentre();
  const { weeks, currentWeek } = useWorkspace();
  if (loading) return <LoadingState />;
  if (error || !centre) return <ErrorState onRetry={reload} />;
  const reported = new Set(centre.data.reports.map((r) => r.week_start));
  const open = weeks.filter((w) => !reported.has(w)).slice(-4);
  return (
    <Wizard
      centre={centre.data}
      provenance={centre.provenance}
      openWeeks={open}
      currentWeek={currentWeek}
    />
  );
}

function Wizard({
  centre,
  provenance,
  openWeeks,
  currentWeek,
}: {
  centre: Schemas["CentreDetail"];
  provenance: Schemas["Provenance"];
  openWeeks: string[];
  currentWeek: string;
}) {
  const t = useTranslations("report");
  const months = useTranslations("months");
  const outbox = useOutbox();
  useProvenance(provenance);
  const firstWeek = openWeeks.includes(currentWeek) ? currentWeek : openWeeks.at(-1);
  const [body, setBody] = useState<ReportBody | null>(
    firstWeek ? startingPoint(centre, firstWeek) : null,
  );
  const [index, setIndex] = useState(0);
  const [check, setCheck] = useState<Schemas["ValidationOut"] | null>(null);
  const [checking, setChecking] = useState(false);
  const [outcome, setOutcome] = useState<{ kind: Outcome; minutes: number } | null>(null);
  const [startedAt] = useState(() => Date.now());
  const finish = (kind: Outcome) =>
    setOutcome({ kind, minutes: Math.max(1, Math.round((Date.now() - startedAt) / 60000)) });

  const step = STEPS[index] as (typeof STEPS)[number];
  const problem = body ? stepProblem(step, body) : null;
  const weekLabel = (w: string) => {
    const { monthKey, day } = weekParts(w);
    return t("weekLabel", { day, month: months(monthKey) });
  };
  const progress = useMemo(() => Math.round((index / (STEPS.length - 1)) * 100), [index]);

  if (!body) {
    return (
      <Panel className="max-w-xl p-6">
        <h1 className="font-display text-2xl text-ink">{t("allDoneTitle")}</h1>
        <p className="mt-2 text-ink-muted">{t("allDoneText")}</p>
        <Link href="/caregiver" className="mt-4 inline-block text-kivu underline">
          {t("backHome")}
        </Link>
      </Panel>
    );
  }

  async function review() {
    if (!body) return;
    setChecking(true);
    try {
      const response = await fetch("/api/reports/check", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      setCheck(response.ok ? ((await response.json()) as Schemas["ValidationOut"]) : null);
    } catch {
      setCheck(null);
    } finally {
      setChecking(false);
    }
  }

  async function submit() {
    if (!body) return;
    const { result, issues } = outbox.online ? await send(body) : { result: "offline" as const };
    if (result === "sent") finish("sent");
    else if (result === "duplicate") finish("duplicate");
    else if (result === "invalid") {
      // Fetch the structured result so warnings can still be confirmed.
      await review();
      if (!issues?.length) setCheck(null);
    } else {
      await outbox.add(body);
      finish("queued");
    }
  }

  if (outcome) {
    const { kind, minutes } = outcome;
    return (
      <Panel className="max-w-xl p-6" role="status">
        <h1 className="font-display text-2xl text-ink">{t(`done.${kind}.title`)}</h1>
        <p className="mt-2 text-ink">
          {t(`done.${kind}.text`, { week: weekLabel(body.week_start) })}
        </p>
        {kind === "sent" && (
          <p className="mt-2 text-sm text-ink-muted">{t("tookMinutes", { minutes })}</p>
        )}
        <ul className="mt-4 flex flex-col gap-1 text-sm text-ink">
          <li>· {t("afterwards.officer")}</li>
          <li>· {t("afterwards.parents")}</li>
          <li>· {t("afterwards.plan")}</li>
        </ul>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/caregiver"
            className="inline-flex min-h-12 items-center rounded-md bg-kivu px-5 font-medium text-white"
          >
            {t("backHome")}
          </Link>
          <Link
            href="/caregiver/sms"
            className="inline-flex min-h-12 items-center rounded-md border border-line-strong px-5 text-ink"
          >
            {t("seeSms")}
          </Link>
        </div>
      </Panel>
    );
  }

  const set = (patch: Partial<ReportBody>) => {
    setBody({ ...body, ...patch });
    setCheck(null);
  };
  const next = async () => {
    const nextIndex = index + 1;
    setIndex(nextIndex);
    if (STEPS[nextIndex]?.key === "review" && outbox.online) await review();
  };

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <div>
        <p className="text-sm text-ink-muted">{centre.name}</p>
        <h1 className="font-display text-2xl text-ink">
          {t("title", { week: weekLabel(body.week_start) })}
        </h1>
      </div>
      <div className="flex items-center gap-3">
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
          aria-label={t("progress", { step: index + 1, total: STEPS.length })}
          className="h-2 flex-1 overflow-hidden rounded-sm bg-line"
        >
          <div className="h-full bg-kivu transition-[width]" style={{ width: `${progress}%` }} />
        </div>
        <span className="tabular text-xs text-ink-muted">
          {index + 1}/{STEPS.length}
        </span>
      </div>
      {!outbox.online && (
        <p className="flex items-center gap-2 rounded-md border border-ochre bg-surface px-3 py-2 text-sm text-ochre-text">
          <CloudOffIcon /> {t("offline")}
        </p>
      )}

      <Panel className="flex flex-col gap-5 p-5">
        <fieldset className="flex flex-col gap-5">
          <legend className="mb-1 text-lg font-semibold text-ink">
            {t(`steps.${step.key}.question`)}
          </legend>
          {index === 1 && <p className="text-sm text-ink-muted">{t("prefilled")}</p>}

          {step.key === "week" && (
            <div className="flex flex-col gap-2">
              {openWeeks.map((w) => (
                <label
                  key={w}
                  className="flex min-h-12 items-center gap-3 rounded-md border border-line-strong px-3"
                >
                  <input
                    type="radio"
                    name="week"
                    checked={body.week_start === w}
                    onChange={() => set({ week_start: w })}
                    className="h-5 w-5 accent-[var(--kivu)]"
                  />
                  <span className="text-ink">
                    {weekLabel(w)}
                    {w === currentWeek ? ` · ${t("thisWeek")}` : ""}
                  </span>
                </label>
              ))}
            </div>
          )}

          {"fields" in step &&
            step.fields.map((field) => (
              <NumberStepper
                key={field}
                label={t(`fields.${field}`)}
                value={body[field]}
                max={step.max}
                onChange={(v) => set({ [field]: v })}
              />
            ))}
          {step.key === "attendance" && (
            <p className="text-sm text-ink-muted">{t("enrolledTotal", { n: enrolled(body) })}</p>
          )}

          {step.key === "water" && (
            <div className="grid grid-cols-2 gap-3">
              {[true, false].map((value) => (
                <label
                  key={String(value)}
                  className={`flex min-h-14 items-center justify-center gap-2 rounded-md border text-lg ${body.wash_available === value ? "border-kivu bg-kivu-tint text-kivu" : "border-line-strong text-ink"}`}
                >
                  <input
                    type="radio"
                    name="wash"
                    className="sr-only"
                    checked={body.wash_available === value}
                    onChange={() => set({ wash_available: value })}
                  />
                  {value ? t("yes") : t("no")}
                </label>
              ))}
            </div>
          )}

          {step.key === "problem" && (
            <div className="flex flex-col gap-2">
              {PROBLEMS.map((p) => (
                <label
                  key={p}
                  className="flex min-h-12 items-center gap-3 rounded-md border border-line-strong px-3"
                >
                  <input
                    type="radio"
                    name="problem"
                    checked={body.main_problem === p}
                    onChange={() => set({ main_problem: p })}
                    className="h-5 w-5 accent-[var(--kivu)]"
                  />
                  <span className="text-ink">{t(`problems.${p}`)}</span>
                </label>
              ))}
            </div>
          )}

          {step.key === "review" && (
            <ReviewStep
              body={body}
              check={check}
              checking={checking}
              online={outbox.online}
              onConfirm={(confirmed) => set({ confirmed })}
            />
          )}
        </fieldset>

        {problem && (
          <p
            role="alert"
            className="rounded-md border border-danger bg-surface px-3 py-2 text-sm text-danger"
          >
            {t(`issue.${problem}`)}
          </p>
        )}
      </Panel>

      <div className="flex gap-3">
        {index > 0 && (
          <Button size="lg" onClick={() => setIndex(index - 1)}>
            {t("back")}
          </Button>
        )}
        {step.key !== "review" ? (
          <Button
            size="lg"
            variant="primary"
            className="flex-1"
            disabled={problem !== null}
            onClick={next}
          >
            {t("next")}
          </Button>
        ) : (
          <Button
            size="lg"
            variant="primary"
            className="flex-1"
            disabled={
              checking ||
              (check !== null &&
                (check.errors.length > 0 || (check.warnings.length > 0 && !body.confirmed)))
            }
            onClick={submit}
          >
            {outbox.online ? t("send") : t("saveOffline")}
          </Button>
        )}
      </div>
    </div>
  );
}

function ReviewStep({
  body,
  check,
  checking,
  online,
  onConfirm,
}: {
  body: ReportBody;
  check: Schemas["ValidationOut"] | null;
  checking: boolean;
  online: boolean;
  onConfirm: (confirmed: boolean) => void;
}) {
  const t = useTranslations("report");
  const rows: [string, string][] = [
    [t("summary.young"), `${body.enrolled_0_2_female + body.enrolled_0_2_male}`],
    [t("summary.old"), `${body.enrolled_3_6_female + body.enrolled_3_6_male}`],
    [t("fields.avg_daily_attendance"), `${body.avg_daily_attendance}`],
    [t("summary.days"), `${body.days_open} / ${body.days_meal_served}`],
    [t("fields.caregivers_present"), `${body.caregivers_present}`],
    [t("fields.waiting_list"), `${body.waiting_list}`],
    [t("summary.water"), body.wash_available ? t("yes") : t("no")],
    [t("summary.problem"), t(`problems.${body.main_problem}`)],
  ];
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-ink-muted">{label}</dt>
            <dd className="tabular text-right text-ink">{value}</dd>
          </div>
        ))}
      </dl>
      {checking && <LoadingState label={t("checking")} />}
      {!online && <p className="text-sm text-ink-muted">{t("offlineCheck")}</p>}
      {check?.errors.map((issue) => (
        <p key={issue.code} role="alert" className="text-sm text-danger">
          {t(`issue.${issue.code}`)}
        </p>
      ))}
      {check && check.warnings.length > 0 && (
        <div className="rounded-md border border-ochre p-3">
          {check.warnings.map((issue) => (
            <p key={issue.code} className="text-sm text-ink">
              {t(`issue.${issue.code}`)}
            </p>
          ))}
          <label className="mt-3 flex min-h-10 items-center gap-2 text-sm font-medium text-ink">
            <input
              type="checkbox"
              checked={body.confirmed ?? false}
              onChange={(e) => onConfirm(e.target.checked)}
              className="h-5 w-5 accent-[var(--kivu)]"
            />
            {t("confirmUnusual")}
          </label>
        </div>
      )}
      {check && check.flags.some((f) => f === "enrolment_jump" || f === "attendance_jump") && (
        <p className="text-sm text-ink-muted">{t("jumpNote")}</p>
      )}
      {check?.accepted && check.warnings.length === 0 && (
        <p className="text-sm text-success">{t("looksGood")}</p>
      )}
    </div>
  );
}
