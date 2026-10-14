"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useMemo } from "react";

import { HatchedChoropleth, type AreaFeature } from "@/components/map/HatchedChoropleth";
import { hatchLevel } from "@/components/map/hatch";
import { useProvenance } from "@/components/shell/ProvenanceProvider";
import { useSession } from "@/components/shell/SessionProvider";
import { SourceChips } from "@/components/signature/SourceChip";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel } from "@/components/ui/Panel";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { api } from "@/lib/api/client";
import { formatNumber, formatRange, formatShare } from "@/lib/format/numbers";
import { useApi } from "@/lib/useApi";

export function NationalOverview() {
  const t = useTranslations("national");
  const map = useTranslations("needMap");
  const router = useRouter();
  const { user } = useSession();
  const areas = useApi(
    "national:areas",
    async () =>
      (
        await api.GET("/geo/areas", {
          params: { query: { parent: "RW", level: "district", detail: "coarse" } },
        })
      ).data ?? null,
  );
  const table = useApi(
    "national:table",
    async () => (await api.GET("/national/districts")).data ?? null,
  );
  useProvenance(areas.data?.provenance);
  useProvenance(table.data?.provenance);
  const features = useMemo<AreaFeature[]>(
    () =>
      (areas.data?.data.features ?? []).map((f) => ({
        id: f.id,
        name: f.properties.name,
        value: f.properties.stunting_risk?.estimate ?? null,
        uncertainty: f.properties.uncertainty,
        geometry: f.geometry as unknown as GeoJSON.Geometry,
      })),
    [areas.data],
  );
  if (areas.loading || table.loading) return <LoadingState />;
  if (!areas.data || !table.data)
    return (
      <ErrorState
        onRetry={() => {
          areas.reload();
          table.reload();
        }}
      />
    );
  // Sector detail and planning exist only for the planner's own district.
  const open = (code: string) => {
    if (code === user?.district_code) router.push("/district");
  };

  return (
    <>
      <PageTitle
        title={t("title")}
        lead={t("lead")}
        actions={
          <a
            href="/api/national/export.csv"
            className="inline-flex min-h-10 items-center rounded-md border border-line-strong bg-surface px-4 text-sm font-medium text-ink"
          >
            {t("download")}
          </a>
        }
      />
      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <HatchedChoropleth
          areas={features}
          title={map("metric.stunting")}
          format={formatShare}
          onSelect={open}
          height={520}
        />
        <Panel className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <caption className="px-4 pt-3 text-left text-xs text-ink-muted">
              {t("tableCaption")}
            </caption>
            <thead className="text-xs text-ink-muted">
              <tr>
                <th scope="col" className="px-3 py-2">
                  {t("district")}
                </th>
                <th scope="col" className="px-3 py-2">
                  {t("children")}
                </th>
                <th scope="col" className="px-3 py-2">
                  {t("stunting")}
                </th>
                <th scope="col" className="px-3 py-2">
                  {t("certainty")}
                </th>
                <th scope="col" className="px-3 py-2">
                  {t("covered")}
                </th>
              </tr>
            </thead>
            <tbody>
              {table.data.data.map((d) => (
                <tr key={d.code} className="border-t border-line">
                  <th scope="row" className="px-3 py-1.5 font-normal">
                    {d.code === user?.district_code ? (
                      <button
                        type="button"
                        onClick={() => open(d.code)}
                        className="text-left text-kivu underline"
                      >
                        {d.name}
                      </button>
                    ) : (
                      d.name
                    )}
                    <span className="block text-xs text-ink-muted">{d.province}</span>
                  </th>
                  <td className="tabular px-3 py-1.5 text-xs">{formatRange(d.children)}</td>
                  <td className="tabular px-3 py-1.5 text-xs">
                    {formatRange(d.stunting_risk, formatShare)}
                  </td>
                  <td className="px-3 py-1.5 text-xs">
                    {map(`certaintyLevel.${hatchLevel(d.uncertainty)}`)}
                  </td>
                  <td className="tabular px-3 py-1.5 text-xs">
                    {d.deep_data ? formatNumber(d.children_covered) : t("noDeepData")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="p-4">
            <SourceChips sources={table.data.provenance.sources} />
          </div>
        </Panel>
      </div>
      <p className="mt-4 text-sm text-ink-muted">{t("note")}</p>
    </>
  );
}
