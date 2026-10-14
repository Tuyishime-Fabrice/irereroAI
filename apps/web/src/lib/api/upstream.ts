import "server-only";

import type { NextResponse } from "next/server";

export const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
export const ACCESS = "irerero_access";
export const REFRESH = "irerero_refresh";

export type Tokens = { access_token: string; refresh_token: string; user: unknown };

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    // INSECURE_COOKIES lets the production build run over plain http on a local machine.
    secure: process.env.NODE_ENV === "production" && process.env.INSECURE_COOKIES !== "true",
    path: "/",
    maxAge,
  };
}

export function withSession<T extends NextResponse>(response: T, tokens: Tokens): T {
  response.cookies.set(ACCESS, tokens.access_token, cookieOptions(60 * 30));
  response.cookies.set(REFRESH, tokens.refresh_token, cookieOptions(60 * 60 * 24 * 7));
  return response;
}

export async function refresh(refreshToken: string): Promise<Tokens | null> {
  const response = await fetch(`${API}/auth/refresh`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
    cache: "no-store",
  });
  return response.ok ? ((await response.json()) as Tokens) : null;
}

/** Calls the API with the access token, refreshing it once if it has expired. */
export async function callWithSession(
  call: (access: string | undefined) => Promise<Response>,
  access: string | undefined,
  refreshToken: string | undefined,
): Promise<{ upstream: Response; renewed: Tokens | null }> {
  let upstream = await call(access);
  let renewed: Tokens | null = null;
  if (upstream.status === 401 && refreshToken) {
    renewed = await refresh(refreshToken);
    if (renewed) upstream = await call(renewed.access_token);
  }
  return { upstream, renewed };
}
