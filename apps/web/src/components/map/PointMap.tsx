"use client";

import type { FeatureCollection } from "geojson";
import type { GeoJSONSource, MapMouseEvent } from "maplibre-gl";
import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";

import { boundsOf, useMapLibre } from "./useMapLibre";

export type MapPoint = {
  id: string;
  lon: number;
  lat: number;
  label: string;
  tone?: "alert" | "warning" | "ok";
};

/**
 * Public map: area outlines, centres and the chosen place. Clicking the map picks a place.
 * The list next to it is the accessible way to the same information.
 */
export function PointMap({
  outlines,
  points,
  place,
  selected,
  onPick,
  onSelect,
  height = 420,
}: {
  outlines: FeatureCollection | null;
  points: MapPoint[];
  place: { lon: number; lat: number } | null;
  selected?: string | null;
  onPick?: (lon: number, lat: number) => void;
  onSelect?: (id: string) => void;
  height?: number;
}) {
  const t = useTranslations("map");
  const container = useRef<HTMLDivElement>(null);
  const { map: mapRef, ready, offline } = useMapLibre(container);
  const fitted = useRef(false);
  const handlers = useRef({ onPick, onSelect });
  useEffect(() => {
    handlers.current = { onPick, onSelect };
  });

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const set = (id: string, data: FeatureCollection) => {
      const source = map.getSource(id) as GeoJSONSource | undefined;
      if (source) source.setData(data);
      else map.addSource(id, { type: "geojson", data });
    };
    set("outlines", outlines ?? { type: "FeatureCollection", features: [] });
    set("centres", {
      type: "FeatureCollection",
      features: points.map((p) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [p.lon, p.lat] },
        properties: { id: p.id, selected: p.id === selected, tone: p.tone ?? "ok" },
      })),
    });
    set("place", {
      type: "FeatureCollection",
      features: place
        ? [
            {
              type: "Feature",
              geometry: { type: "Point", coordinates: [place.lon, place.lat] },
              properties: {},
            },
          ]
        : [],
    });
    if (!map.getLayer("outline-line")) {
      map.addLayer({
        id: "outline-fill",
        type: "fill",
        source: "outlines",
        paint: { "fill-color": "#FFFDF9", "fill-opacity": 0.35 },
      });
      map.addLayer({
        id: "outline-line",
        type: "line",
        source: "outlines",
        paint: { "line-color": "#6B6259", "line-width": 0.8 },
      });
      map.addLayer({
        id: "centres",
        type: "circle",
        source: "centres",
        paint: {
          "circle-radius": ["case", ["get", "selected"], 9, 6],
          "circle-color": [
            "match",
            ["get", "tone"],
            "alert",
            "#B3261E",
            "warning",
            "#C98B2B",
            "#1D5C63",
          ],
          "circle-stroke-color": "#FFFDF9",
          "circle-stroke-width": 2,
        },
      });
      map.addLayer({
        id: "place",
        type: "circle",
        source: "place",
        paint: {
          "circle-radius": 8,
          "circle-color": "#B4472B",
          "circle-stroke-color": "#1E1B18",
          "circle-stroke-width": 2,
        },
      });
      map.on("click", (event: MapMouseEvent) => {
        const hit = map.queryRenderedFeatures(event.point, { layers: ["centres"] })[0];
        const id = hit?.properties?.id;
        if (typeof id === "string") handlers.current.onSelect?.(id);
        else handlers.current.onPick?.(event.lngLat.lng, event.lngLat.lat);
      });
    }
    if (!fitted.current && outlines?.features.length) {
      const bounds = boundsOf(outlines.features.map((f) => f.geometry));
      if (bounds) map.fitBounds(bounds, { padding: 16, duration: 0 });
      fitted.current = true;
    }
  }, [ready, outlines, points, place, selected, mapRef]);

  useEffect(() => {
    const map = mapRef.current;
    if (map && ready && place)
      map.easeTo({ center: [place.lon, place.lat], zoom: Math.max(map.getZoom(), 11) });
  }, [place, ready, mapRef]);

  return (
    <div className="relative overflow-hidden rounded-md border border-line" style={{ height }}>
      <div
        ref={container}
        className="h-full w-full"
        role="region"
        aria-label={t("findLabel", { count: points.length })}
      />
      {offline && (
        <p className="absolute top-3 left-3 rounded-sm bg-surface/90 px-2 py-1 text-xs text-ink-muted">
          {t("offlineBasemap")}
        </p>
      )}
    </div>
  );
}
