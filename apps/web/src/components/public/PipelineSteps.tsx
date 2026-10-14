import { getTranslations } from "next-intl/server";

const STEPS = ["sources", "alignment", "models", "suggestions", "decision", "feedback"] as const;

/** The full data process, each step saying what is real today and what is simulated. */
export async function PipelineSteps() {
  const t = await getTranslations("methodology.steps");
  return (
    <ol className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
      {STEPS.map((step, i) => (
        <li
          key={step}
          className="relative flex flex-col gap-2 rounded-md border border-line bg-surface p-4"
        >
          <span className="font-mono text-xs text-clay">0{i + 1}</span>
          <h2 className="font-display text-lg text-ink">{t(`${step}.title`)}</h2>
          <p className="text-sm text-ink">{t(`${step}.what`)}</p>
          <p className="mt-auto border-t border-line pt-2 text-xs text-ink-muted">
            <span className="font-semibold text-clay">{t("todayLabel")}</span> {t(`${step}.today`)}
          </p>
          <p className="text-xs text-ink-muted">
            <span className="font-semibold text-kivu">{t("phase2Label")}</span>{" "}
            {t(`${step}.phase2`)}
          </p>
        </li>
      ))}
    </ol>
  );
}
