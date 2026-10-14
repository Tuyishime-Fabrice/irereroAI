import { getTranslations } from "next-intl/server";
import Link from "next/link";

import { CycleDiagram } from "@/components/public/CycleDiagram";
import { HeadlineNumbers } from "@/components/public/HeadlineNumbers";
import { ZigzagBand } from "@/components/brand/ZigzagBand";
import { Panel } from "@/components/ui/Panel";

export default async function Landing() {
  const t = await getTranslations("landing");
  return (
    <div className="flex flex-col gap-14">
      <section className="grid gap-8 pt-4 lg:grid-cols-[1.2fr_1fr] lg:items-center">
        <div>
          <ZigzagBand className="mb-5 max-w-24 rounded-sm" />
          <h1 className="font-display text-4xl leading-tight font-semibold text-ink sm:text-5xl">
            {t("title")}
          </h1>
          <p className="mt-4 max-w-xl text-lg text-ink-muted">{t("lead")}</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/find"
              className="inline-flex min-h-12 items-center rounded-md bg-kivu px-5 font-medium text-white"
            >
              {t("ctaFind")}
            </Link>
            <Link
              href="/sign-in"
              className="inline-flex min-h-12 items-center rounded-md border border-line-strong bg-surface px-5 font-medium text-ink"
            >
              {t("ctaStaff")}
            </Link>
            <Link
              href="/tour"
              className="inline-flex min-h-12 items-center rounded-md px-3 font-medium text-kivu underline"
            >
              {t("ctaTour")}
            </Link>
          </div>
        </div>
        <CycleDiagram />
      </section>

      <section aria-labelledby="numbers" data-tour="numbers">
        <h2 id="numbers" className="mb-4 font-display text-2xl text-ink">
          {t("numbersTitle")}
        </h2>
        <HeadlineNumbers />
      </section>

      <section aria-labelledby="promise" className="grid gap-6 lg:grid-cols-2">
        <Panel className="p-6" data-tour="promise">
          <h2 id="promise" className="mb-3 font-display text-2xl text-ink">
            {t("promiseTitle")}
          </h2>
          <ul className="flex flex-col gap-2 text-ink">
            {(["suggests", "reasons", "reject", "audit", "nothingAutomatic"] as const).map(
              (key) => (
                <li key={key} className="flex gap-2">
                  <span aria-hidden className="mt-2 h-2 w-2 shrink-0 rotate-45 bg-kivu" />
                  {t(`promise.${key}`)}
                </li>
              ),
            )}
          </ul>
        </Panel>
        <Panel className="border-clay p-6">
          <h2 className="mb-3 font-display text-2xl text-ink">{t("honestyTitle")}</h2>
          <div className="flex flex-col gap-2 text-ink">
            <p>{t("honesty.simulated")}</p>
            <p>{t("honesty.real")}</p>
            <p>{t("honesty.phase2")}</p>
            <p>{t("honesty.privacy")}</p>
          </div>
          <Link href="/methodology" className="mt-3 inline-block text-kivu underline">
            {t("honestyLink")}
          </Link>
        </Panel>
      </section>

      <section aria-labelledby="who">
        <h2 id="who" className="mb-4 font-display text-2xl text-ink">
          {t("whoTitle")}
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {(["parents", "caregivers", "officers", "planners"] as const).map((key) => (
            <Panel key={key} className="flex flex-col gap-2 p-5">
              <h3 className="font-semibold text-ink">{t(`who.${key}.title`)}</h3>
              <p className="text-sm text-ink-muted">{t(`who.${key}.text`)}</p>
              <Link
                href={key === "parents" ? "/find" : "/sign-in"}
                className="mt-auto text-sm font-medium text-kivu underline"
              >
                {t(`who.${key}.link`)}
              </Link>
            </Panel>
          ))}
        </div>
        <p className="mt-4 text-sm text-ink-muted">{t("ncda")}</p>
      </section>
    </div>
  );
}
