"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import {
  HatchedChoropleth,
  type AreaFeature,
  type PointLayer,
} from "@/components/map/HatchedChoropleth";
import { hatchLevel } from "@/components/map/hatch";
import { useProvenance } from "@/components/shell/ProvenanceProvider";
import { useWorkspace } from "@/components/shell/Workspace";
import { RangeBar } from "@/components/signature/RangeBar";
import { SourceChips } from "@/components/signature/SourceChip";
import { WeekScrubber } from "@/components/signature/WeekScrubber";
import { SelectField } from "@/components/ui/Field";
import { PageTitle } from "@/components/ui/PageTitle";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { api, type Schemas } from "@/lib/api/client";
import { formatNumber, formatShare } from "@/lib/format/numbers";
import { useApi } from "@/lib/useApi";

import { useDistrictCode } from "./useDistrict";

type Area = Schemas["AreaProperties"];
const METRICS = ["children", "stunting", "uncovered", "mothers"] as const;
type Metric = (typeof METRICS)[number];
const LAYERS = ["centres", "demand", "sites"] as const;

function value(area: Area, metric: Metric): number | null {
  if (metric === "children") return area.children?.estimate ?? null;
  if (metric === "stunting") return area.stunting_risk?.estimate ?? null;
  if (metric === "uncovered") return area.children_uncovered;
  return area.mothers_barrier_share?.estimate ?? null;
}

export function NeedMap() {
  const t = useTranslations("needMap");
  const district = useDistrictCode();
  const { week, weeks, setWeek } = useWorkspace();
  const [metric, setMetric] = useState<Metric>("stunting");
  const [layers, setLayers] = useState<Set<string>>(new Set(["centres", "demand"]));
  const [selected, setSelected] = useState<string | null>(null);

  const areas = useApi(
    `areas:${district}:${week}`,
    async () =>
      (await api.GET("/geo/areas", { params: { query: { parent: district, week } } })).data ?? null,
  );
  const centres = useApi(
    `gcentres:${district}:${week}`,
    async () =>
      (await api.GET("/geo/centres", { params: { query: { area: district, week } } })).data ?? null,
  );
  const demand = useApi(
    `demand:${district}:${week}`,
    async () =>
      (await api.GET("/geo/demand", { params: { query: { area: district, week } } })).data ?? null,
  );
  const sites = useApi(
    `sites:${district}`,
    async () =>
      (await api.GET("/geo/sites", { params: { query: { area: district } } })).data ?? null,
  );
  useProvenance(areas.data?.provenance);
  useProvenance(centres.data?.provenance);

  const features = useMemo<AreaFeature[]>(
    () =>
      (areas.data?.data.features ?? []).map((f) => ({
        id: f.id,
        name: f.properties.name,
        value: value(f.properties, metric),
        uncertainty: f.properties.uncertainty,
        geometry: f.geometry as unknown as GeoJSON.Geometry,
      })),
    [areas.data, metric],
  );
  const pointLayers = useMemo<PointLayer[]>(() => {
    const out: PointLayer[] = [];
    const coords = (g: Record<string, unknown>) =>
      (g as { coordinates: [number, number] }).coordinates;
    if (layers.has("centres") && centres.data) {
      out.push({
        id: "centres",
        points: centres.data.data.features.map((f) => ({
          id: f.id,
          lon: coords(f.geometry)[0],
          lat: coords(f.geometry)[1],
          label: f.properties.name,
          tone:
            f.properties.alert_severity === "critical" || f.properties.overcrowded ? "alert" : "ok",
        })),
      });
    }
    if (layers.has("demand") && demand.data) {
      out.push({
        id: "demand",
        points: demand.data.data.features.map((f) => ({
          id: f.id,
          lon: coords(f.geometry)[0],
          lat: coords(f.geometry)[1],
          label: f.id,
        })),
      });
    }
    if (layers.has("sites") && sites.data) {
      out.push({
        id: "sites",
        points: sites.data.data.features.map((f) => ({
          id: f.id,
          lon: coords(f.geometry)[0],
          lat: coords(f.geometry)[1],
          label: f.properties.name,
        })),
      });
    }
    return out;
  }, [layers, centres.data, demand.data, sites.data]);

  if (areas.loading) return <LoadingState />;
  if (areas.error || !areas.data) return <ErrorState onRetry={areas.reload} />;
  const area = areas.data.data.features.find((f) => f.id === selected)?.properties;
  const format = metric === "stunting" || metric === "mothers" ? formatShare : formatNumber;
  const demandTotal =
    demand.data?.data.features.reduce(
      (n, f) => n + f.properties.empty_searches + f.properties.centre_requests,
      0,
    ) ?? 0;

  return (
    <>
      <PageTitle title={t("title")} lead={t("lead")} />
      <div className="mb-4 grid gap-3 lg:grid-cols-[240px_1fr]">
        <SelectField
          label={t("measure")}
          value={metric}
          onChange={(e) => setMetric(e.target.value as Metric)}
        >
          {METRICS.map((m) => (
            <option key={m} value={m}>
              {t(`metric.${m}`)}
            </option>
          ))}
        </SelectField>
        <div className="flex flex-col gap-2">
          <div data-tour="week-scrubber">
            <WeekScrubber weeks={weeks} value={week} onChange={setWeek} />
          </div>
          <fieldset className="flex flex-wrap gap-4 text-sm">
            <legend className="sr-only">{t("layers")}</legend>
            {LAYERS.map((layer) => (
              <label key={layer} className="flex min-h-9 items-center gap-2">
                <input
                  type="checkbox"
                  checked={layers.has(layer)}
                  onChange={(e) => {
                    const next = new Set(layers);
                    if (e.target.checked) next.add(layer);
                    else next.delete(layer);
                    setLayers(next);
                  }}
                  className="h-4 w-4 accent-[var(--kivu)]"
                />
                {t(`layer.${layer}`)}
              </label>
            ))}
            <span className="text-ink-muted">{t("demandCount", { n: demandTotal })}</span>
          </fieldset>
        </div>
      </div>
      <div className="grid gap-6 xl:grid-cols-[1fr_340px]" data-tour="need-map">
        <HatchedChoropleth
          areas={features}
          title={t(`metric.${metric}`)}
          format={format}
          pointLayers={pointLayers}
          selected={selected}
          onSelect={setSelected}
          height={540}
        />
        <Panel className="self-start">
          <PanelHeader title={area ? area.name : t("pickSector")} />
          {!area ? (
            <EmptyState title={t("pickHint")} />
          ) : (
            <dl className="flex flex-col gap-4 p-4 text-sm">
              {area.children && (
                <div>
                  <dt className="text-xs text-ink-muted">{t("metric.children")}</dt>
                  <dd>
                    <RangeBar value={area.children} max={area.children.high * 1.2} />
                  </dd>
                </div>
              )}
              {area.stunting_risk && (
                <div>
                  <dt className="text-xs text-ink-muted">{t("metric.stunting")}</dt>
                  <dd>
                    <RangeBar value={area.stunting_risk} max={1} format={formatShare} />
                  </dd>
                </div>
              )}
              {area.mothers_barrier_share && (
                <div>
                  <dt className="text-xs text-ink-muted">{t("metric.mothers")}</dt>
                  <dd>
                    <RangeBar value={area.mothers_barrier_share} max={1} format={formatShare} />
                  </dd>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <dt className="text-xs text-ink-muted">{t("covered")}</dt>
                  <dd className="tabular">{formatNumber(area.children_covered)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-muted">{t("metric.uncovered")}</dt>
                  <dd className="tabular">{formatNumber(area.children_uncovered)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-muted">{t("centres")}</dt>
                  <dd className="tabular">{area.centres}</dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-muted">{t("demand")}</dt>
                  <dd className="tabular">{area.demand_signals}</dd>
                </div>
              </div>
              <div>
                <dt className="text-xs text-ink-muted">{t("certainty")}</dt>
                <dd>{t(`certaintyLevel.${hatchLevel(area.uncertainty)}`)}</dd>
              </div>
            </dl>
          )}
          <div className="border-t border-line p-4">
            <SourceChips sources={areas.data.provenance.sources} />
          </div>
        </Panel>
      </div>
      <p className="mt-4 text-sm text-ink-muted">{t("replayNote")}</p>
    </>
  );
}
