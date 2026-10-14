"use client";

import "maplibre-gl/dist/maplibre-gl.css";

import type { Map as MapLibreMap } from "maplibre-gl";
import { useEffect, useRef, useState, type RefObject } from "react";

import { hatchImage } from "./hatch";
import { BASEMAP_URL, OFFLINE_STYLE } from "./style";

const BASEMAP_TIMEOUT_MS = 5000;

/**
 * Creates a MapLibre map in the container. Falls back to the boundaries-only style when the
 * basemap cannot load (offline, blocked, or not configured), so the demo works without network.
 * `ready` turns true each time a style has loaded and our images are registered.
 */
export function useMapLibre(container: RefObject<HTMLDivElement | null>) {
  const mapRef = useRef<MapLibreMap | null>(null);
  const [ready, setReady] = useState(0);
  const [offline, setOffline] = useState(!BASEMAP_URL);

  useEffect(() => {
    const element = container.current;
    if (!element) return;
    let map: MapLibreMap | null = null;
    let timer = 0;
    let cancelled = false;
    // Loaded on demand so the page and its list render before the map library arrives.
    void import("maplibre-gl").then(({ Map, NavigationControl, setWorkerUrl }) => {
      if (cancelled) return;
      // Served from public/ (copied there at build time by scripts/copy-maplibre-worker.mjs).
      setWorkerUrl("/maplibre-gl-worker.mjs");
      const created = new Map({
        container: element,
        style: BASEMAP_URL || OFFLINE_STYLE,
        attributionControl: { compact: true },
        dragRotate: false,
        pitchWithRotate: false,
      });
      map = created;
      mapRef.current = created;
      created.addControl(new NavigationControl({ showCompass: false }), "top-right");
      const useOffline = () => {
        if (created.isStyleLoaded()) return;
        setOffline(true);
        created.setStyle(OFFLINE_STYLE);
      };
      timer = window.setTimeout(useOffline, BASEMAP_TIMEOUT_MS);
      created.on("error", useOffline);
      created.on("style.load", () => {
        for (const level of [1, 2, 3]) {
          if (!created.hasImage(`hatch-${level}`)) {
            created.addImage(`hatch-${level}`, hatchImage(level), { pixelRatio: 2 });
          }
        }
        setReady((count) => count + 1);
      });
    });
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      map?.remove();
      mapRef.current = null;
    };
  }, [container]);

  return { map: mapRef, ready: ready > 0 ? ready : 0, offline };
}

export function boundsOf(geometries: GeoJSON.Geometry[]): [number, number, number, number] | null {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  const visit = (coords: unknown): void => {
    if (typeof (coords as number[])[0] === "number") {
      const [x, y] = coords as [number, number];
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
      return;
    }
    (coords as unknown[]).forEach(visit);
  };
  geometries.forEach((g) => "coordinates" in g && visit(g.coordinates));
  return Number.isFinite(minX) ? [minX, minY, maxX, maxY] : null;
}
