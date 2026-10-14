import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

/** Typed client for the browser. Requests go through the same-origin proxy at /api. */
export const api = createClient<paths>({ baseUrl: "/api" });

export type Schemas = components["schemas"];
export type Me = Schemas["Me"];
export type Provenance = Schemas["Provenance"];
export type Origin = Schemas["Origin"];
export type RangeValue = Schemas["RangeOut"];
export type DriverValue = Schemas["DriverOut"];
export type SourceValue = Schemas["SourceOut"];
