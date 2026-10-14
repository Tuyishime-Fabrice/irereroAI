/** The signed-in user, or null. Answers without calling the API when there is no session. */
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACCESS, API, callWithSession, REFRESH, withSession } from "@/lib/api/upstream";

export async function GET() {
  const jar = await cookies();
  const access = jar.get(ACCESS)?.value;
  const refreshToken = jar.get(REFRESH)?.value;
  if (!access && !refreshToken) return NextResponse.json(null);
  const { upstream, renewed } = await callWithSession(
    (token) =>
      fetch(`${API}/auth/me`, {
        headers: token ? { authorization: `Bearer ${token}` } : {},
        cache: "no-store",
      }),
    access,
    refreshToken,
  );
  const response = NextResponse.json(upstream.ok ? await upstream.json() : null);
  return renewed ? withSession(response, renewed) : response;
}
