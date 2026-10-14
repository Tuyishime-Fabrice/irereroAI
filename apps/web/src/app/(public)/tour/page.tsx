import { getTranslations } from "next-intl/server";

import { TOUR } from "@/components/tour/steps";
import { StartTour } from "@/components/tour/StartTour";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel } from "@/components/ui/Panel";

export async function generateMetadata() {
  const t = await getTranslations("tour");
  return { title: t("title") };
}

export default async function TourPage() {
  const t = await getTranslations("tour");
  return (
    <>
      <PageTitle title={t("title")} lead={t("lead")} actions={<StartTour />} />
      <ol className="grid gap-3 md:grid-cols-2">
        {TOUR.map((step, i) => (
          <li key={step.key}>
            <Panel className="h-full p-4">
              <p className="font-mono text-xs text-clay">
                {String(i + 1).padStart(2, "0")}
                {step.role && ` · ${t(`as.${step.role}`)}`}
              </p>
              <h2 className="font-display text-lg text-ink">{t(`steps.${step.key}.title`)}</h2>
              <p className="mt-1 text-sm text-ink">{t(`steps.${step.key}.text`)}</p>
              <p className="mt-2 text-xs text-ink-muted">{t(`steps.${step.key}.say`)}</p>
            </Panel>
          </li>
        ))}
      </ol>
      <p className="mt-6 text-sm text-ink-muted">{t("offline")}</p>
    </>
  );
}
