"use client";

import { useSession } from "@/components/shell/SessionProvider";
import { api } from "@/lib/api/client";
import { useApi } from "@/lib/useApi";

/** The signed-in caregiver's own centre, with its reports and alerts. */
export function useMyCentre() {
  const { user } = useSession();
  const code = user?.scope_code ?? null;
  return useApi(code && `centre:${code}`, async () => {
    if (!code) return null;
    const { data } = await api.GET("/centres/{code}", { params: { path: { code } } });
    return data ?? null;
  });
}
