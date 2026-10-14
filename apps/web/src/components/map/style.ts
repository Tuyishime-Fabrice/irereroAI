import type { StyleSpecification } from "maplibre-gl";

export const BASEMAP_URL = process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? "";

/** No tiles, no fonts: the boundaries alone. Used offline and when the basemap fails. */
export const OFFLINE_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "paper", type: "background", paint: { "background-color": "#F6F1E9" } }],
};
