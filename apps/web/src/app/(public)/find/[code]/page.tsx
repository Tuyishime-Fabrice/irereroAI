import { getTranslations } from "next-intl/server";
import Link from "next/link";
import { notFound } from "next/navigation";

import { RegisterProvenance } from "@/components/shell/RegisterProvenance";
import { SourceChips } from "@/components/signature/SourceChip";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel } from "@/components/ui/Panel";
import { serverApi } from "@/lib/api/server";

export const dynamic = "force-dynamic";

export default async function CentrePage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  const t = await getTranslations("find");
  const { data } = await serverApi.GET("/public/centres/{code}", { params: { path: { code } } });
  if (!data) notFound();
  const c = data.data;
  const count = (value: typeof c.capacity | null) =>
    value === null ? t("notReported") : value.suppressed ? t("fewerThanFive") : String(value.value);
  const facts: [string, string][] = [
    [t("typeLabel"), t(`type.${c.type}`)],
    [
      t("agesLabel"),
      c.serves_0_2 && c.serves_3_6
        ? t("ages.both")
        : c.serves_0_2
          ? t("ages.young")
          : t("ages.old"),
    ],
    [t("hours"), c.opening_hours],
    [t("feeLabel"), t(`fee.${c.fee_band}`)],
    [t("capacity"), count(c.capacity)],
    [t("freePlaces"), count(c.free_places)],
    [t("mealsLabel"), c.offers_meals ? t("yes") : t("no")],
    [t("growth"), c.offers_growth_monitoring ? t("yes") : t("no")],
    [t("inclusive"), c.disability_inclusive ? t("yes") : t("no")],
    [t("lastVerified"), c.verified_at ? c.verified_at.slice(0, 10) : t("notVerified")],
  ];
  return (
    <>
      <RegisterProvenance provenance={data.provenance} />
      <Link href="/find" className="text-sm text-kivu underline">
        ← {t("backToFind")}
      </Link>
      <div className="mt-4">
        <PageTitle title={c.name} lead={`${c.sector_name}`} />
      </div>
      <Panel className="max-w-2xl p-5">
        <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
          {facts.map(([label, value]) => (
            <div key={label}>
              <dt className="text-xs text-ink-muted">{label}</dt>
              <dd className="text-ink">{value}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-4 text-sm text-ink-muted">{t("freePlacesNote")}</p>
        <div className="mt-4">
          <SourceChips sources={data.provenance.sources} />
        </div>
      </Panel>
    </>
  );
}
