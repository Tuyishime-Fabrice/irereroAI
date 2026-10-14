import { getTranslations } from "next-intl/server";

const STEPS = ["plan", "track", "find", "learn"] as const;

/** Plan, Track, Find, Learn as a loop: each step feeds the next, and Learn feeds Plan. */
export async function CycleDiagram() {
  const t = await getTranslations("landing.cycle");
  return (
    <figure
      aria-labelledby="cycle-caption"
      className="rounded-md border border-line bg-surface p-5"
    >
      <ol className="grid grid-cols-2 gap-3">
        {STEPS.map((step, i) => (
          <li key={step} className="relative rounded-md border border-line bg-paper p-4">
            <span className="font-mono text-xs text-clay">0{i + 1}</span>
            <p className="font-display text-xl text-ink">{t(`${step}.title`)}</p>
            <p className="mt-1 text-sm text-ink-muted">{t(`${step}.text`)}</p>
          </li>
        ))}
      </ol>
      <figcaption id="cycle-caption" className="mt-3 text-sm text-ink-muted">
        {t("caption")}
      </figcaption>
    </figure>
  );
}
