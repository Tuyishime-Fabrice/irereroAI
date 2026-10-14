// MapLibre 6 loads its web worker from a file next to its own bundle, which the Next bundler
// does not emit. Copy the self-contained worker into public/ so it is served at a fixed URL.
import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const dist = dirname(require.resolve("maplibre-gl/dist/maplibre-gl.css"));
mkdirSync("public", { recursive: true });
copyFileSync(join(dist, "maplibre-gl-worker.mjs"), join("public", "maplibre-gl-worker.mjs"));
