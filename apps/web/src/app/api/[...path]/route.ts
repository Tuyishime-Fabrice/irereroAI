/**
 * Same-origin proxy to the API. Tokens live in httpOnly cookies and never reach page scripts:
 * sign-in responses are stripped to the user, and an expired access token is refreshed once.
 */
import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";

import {
  ACCESS,
  API,
  callWithSession,
  REFRESH,
  withSession,
  type Tokens,
} from "@/lib/api/upstream";

const SIGN_IN = [/^auth\/login$/, /^auth\/caregiver$/, /^auth\/otp\/verify$/, /^demo\/login\/\w+$/];

async function forward(request: NextRequest, path: string, access: string | undefined) {
  const headers = new Headers();
  const type = request.headers.get("content-type");
  if (type) headers.set("content-type", type);
  if (access) headers.set("authorization", `Bearer ${access}`);
  const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.clone().text();
  return fetch(`${API}/${path}${request.nextUrl.search}`, {
    method: request.method,
    headers,
    body,
    cache: "no-store",
  });
}

function relay(upstream: Response, body: BodyInit | null) {
  const headers = new Headers();
  for (const name of ["content-type", "content-disposition"]) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  return new NextResponse(body, { status: upstream.status, headers });
}

async function handle(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path.join("/");
  const jar = await cookies();

  if (path === "auth/logout") {
    await forward(request, path, jar.get(ACCESS)?.value);
    const response = new NextResponse(null, { status: 204 });
    response.cookies.delete(ACCESS);
    response.cookies.delete(REFRESH);
    return response;
  }

  const { upstream, renewed } = await callWithSession(
    (access) => forward(request, path, access),
    jar.get(ACCESS)?.value,
    jar.get(REFRESH)?.value,
  );
  if (upstream.ok && SIGN_IN.some((pattern) => pattern.test(path))) {
    const tokens = (await upstream.json()) as Tokens;
    return withSession(NextResponse.json({ user: tokens.user }), tokens);
  }
  const response = relay(upstream, upstream.status === 204 ? null : await upstream.arrayBuffer());
  return renewed ? withSession(response, renewed) : response;
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
