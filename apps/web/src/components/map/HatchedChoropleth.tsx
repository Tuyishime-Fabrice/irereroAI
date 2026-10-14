"use client";

import type { FeatureCollection } from "geojson";
import type { GeoJSONSource } from "maplibre-gl";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useRef } from "react";

import { classOf, NEED_COLOURS, quantileBreaks } from "./classes";
import { hatchLevel } from "./hatch";
import { Legend } from "./Legend";
import { boundsOf, useMapLibre } from "./useMapLibre";

export type AreaFeature = {
  id: string;
  name: string;
  value: number | null;
  uncertainty: number | null;
  geometry: GeoJSON.Geometry;
};

export type PointLayer = {
  id: "centres" | "demand" | "sites" | "highlight";
  points: {
    id: string;
    lon: number;
    lat: number;
    label: string;
    tone?: "alert" | "ok" | "muted";
  }[];
};

const POINT_STYLE = {
  centres: { radius: 5, colour: "#1D5C63", stroke: "#FFFDF9" },
  demand: { radius: 6, colour: "rgba(180, 71, 43, 0.25)", stroke: "#B4472B" },
  sites: { radius: 4, colour: "#FFFDF9", stroke: "#1E1B18" },
  highlight: { radius: 9, colour: "rgba(0,0,0,0)", stroke: "#1D5C63" },
} as const;

/**
 * Areas coloured by a need measure in five steps, hatched where the estimate is uncertain.
 * Point layers (centres, parent demand, candidate sites) sit on top. A table alternative is
 * always rendered for screen readers and keyboard users.
 */
export function HatchedChoropleth({
  areas,
  title,
  format,
  pointLayers = [],
  selected,
  onSelect,
  height = 460,
}: {
  areas: AreaFeature[];
  title: string;
  format: (value: number) => string;
  pointLayers?: PointLayer[];
  selected?: string | null;
  onSelect?: (id: string) => void;
  height?: number;
}) {
  const t = useTranslations("map");
  const container = useRef<HTMLDivElement>(null);
  const { map: mapRef, ready, offline } = useMapLibre(container);
  const fitted = useRef(false);

  const breaks = useMemo(
    () => quantileBreaks(areas.map((a) => a.value).filter((v): v is number => v !== null)),
    [areas],
  );
  const areaData = useMemo<FeatureCollection>(
    () => ({
      type: "FeatureCollection",
      features: areas.map((a) => ({
        type: "Feature",
        id: a.id,
        geometry: a.geometry,
        properties: {
          id: a.id,
          name: a.name,
          step: a.value === null ? -1 : classOf(a.value, breaks),
          hatch: hatchLevel(a.uncertainty),
          selected: a.id === selected,
        },
      })),
    }),
    [areas, breaks, selected],
  );

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const source = map.getSource("areas") as GeoJSONSource | undefined;
    if (source) {
      source.setData(areaData);
    } else {
      map.addSource("areas", { type: "geojson", data: areaData });
      map.addLayer({
        id: "area-fill",
        type: "fill",
        source: "areas",
        paint: {
          "fill-color": [
            "match",
            ["get", "step"],
            0,
            NEED_COLOURS[0],
            1,
            NEED_COLOURS[1],
            2,
            NEED_COLOURS[2],
            3,
            NEED_COLOURS[3],
            4,
            NEED_COLOURS[4],
            "#E3D9CB",
          ],
          "fill-opacity": 0.88,
        },
      });
      for (const level of [1, 2, 3]) {
        map.addLayer({
          id: `area-hatch-${level}`,
          type: "fill",
          source: "areas",
          filter: ["==", ["get", "hatch"], level],
          paint: { "fill-pattern": `hatch-${level}` },
        });
      }
      map.addLayer({
        id: "area-line",
        type: "line",
        source: "areas",
        paint: {
          "line-color": ["case", ["get", "selected"], "#1D5C63", "#1E1B18"],
          "line-width": ["case", ["get", "selected"], 3, 0.6],
        },
      });
      map.on("click", "area-fill", (event) => {
        const id = event.features?.[0]?.properties?.id;
        if (typeof id === "string") onSelect?.(id);
      });
      map.on(
        "mouseenter",
        "area-fill",
        () => (map.getCanvas().style.cursor = onSelect ? "pointer" : ""),
      );
      map.on("mouseleave", "area-fill", () => (map.getCanvas().style.cursor = ""));
    }
    if (!fitted.current) {
      const bounds = boundsOf(areas.map((a) => a.geometry));
      if (bounds) map.fitBounds(bounds, { padding: 24, duration: 0 });
      fitted.current = true;
    }
  }, [ready, areaData, areas, onSelect, mapRef]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    for (const id of Object.keys(POINT_STYLE) as PointLayer["id"][]) {
      const layer = pointLayers.find((l) => l.id === id);
      const data: FeatureCollection = {
        type: "FeatureCollection",
        features: (layer?.points ?? []).map((p) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [p.lon, p.lat] },
          properties: { id: p.id, label: p.label, tone: p.tone ?? "ok" },
        })),
      };
      const source = map.getSource(`points-${id}`) as GeoJSONSource | undefined;
      if (source) {
        source.setData(data);
        continue;
      }
      const style = POINT_STYLE[id];
      map.addSource(`points-${id}`, { type: "geojson", data });
      map.addLayer({
        id: `points-${id}`,
        type: "circle",
        source: `points-${id}`,
        paint: {
          "circle-radius": style.radius,
          "circle-color":
            id === "centres"
              ? ["match", ["get", "tone"], "alert", "#B3261E", "muted", "#6B6259", style.colour]
              : style.colour,
          "circle-stroke-color": style.stroke,
          "circle-stroke-width": id === "highlight" ? 3 : 1.5,
        },
      });
    }
  }, [ready, pointLayers, mapRef]);

  const sorted = [...areas].sort((a, b) => (b.value ?? -1) - (a.value ?? -1));
  const labels = [0, 1, 2, 3, 4].map((i) => {
    const low = i === 0 ? Math.min(...areas.map((a) => a.value ?? Infinity)) : breaks[i - 1];
    return low === undefined || !Number.isFinite(low) ? "" : `≥ ${format(low)}`;
  });

  return (
    <div className="flex flex-col gap-3">
      <div className="relative overflow-hidden rounded-md border border-line" style={{ height }}>
        <div
          ref={container}
          className="h-full w-full"
          role="region"
          aria-label={t("mapLabel", { title, count: areas.length })}
        />
        <div className="absolute bottom-3 left-3 max-w-60">
          <Legend
            title={title}
            labels={labels}
            showHatch={areas.some((a) => hatchLevel(a.uncertainty) > 0)}
          />
        </div>
        {offline && (
          <p className="absolute top-3 left-3 rounded-sm bg-surface/90 px-2 py-1 text-xs text-ink-muted">
            {t("offlineBasemap")}
          </p>
        )}
      </div>
      <details className="text-sm">
        <summary className="cursor-pointer text-kivu">{t("showTable")}</summary>
        <table className="mt-2 w-full text-left text-sm">
          <caption className="sr-only">{title}</caption>
          <thead className="text-xs text-ink-muted">
            <tr>
              <th scope="col" className="py-1">
                {t("area")}
              </th>
              <th scope="col" className="py-1">
                {title}
              </th>
              <th scope="col" className="py-1">
                {t("uncertainty")}
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((area) => (
              <tr key={area.id} className="border-t border-line">
                <th scope="row" className="py-1 font-normal">
                  {onSelect ? (
                    <button
                      type="button"
                      className="text-left text-kivu underline"
                      onClick={() => onSelect(area.id)}
                    >
                      {area.name}
                    </button>
                  ) : (
                    area.name
                  )}
                </th>
                <td className="tabular py-1">{area.value === null ? "–" : format(area.value)}</td>
                <td className="py-1">{t(`hatchLevel.${hatchLevel(area.uncertainty)}`)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  );
}
