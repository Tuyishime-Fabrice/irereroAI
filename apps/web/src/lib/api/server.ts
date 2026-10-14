import "server-only";

import createClient from "openapi-fetch";

import type { paths } from "./schema";

/** Typed client for server components: public data only, straight to the API. */
export const serverApi = createClient<paths>({
  baseUrl: process.env.API_INTERNAL_URL ?? "http://localhost:8000",
});
