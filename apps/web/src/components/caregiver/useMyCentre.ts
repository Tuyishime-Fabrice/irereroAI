"use client";

import { useSession } from "@/components/shell/SessionProvider";
import { api } from "@/lib/api/client";
import { useApi } from "@/lib/useApi";

/** A centre's detail with reports and alerts: the caregiver's own centre unless one is named. */
export function useMyCentre(centreCode?: string) {
  const { user } = useSession();
  const code = centreCode ?? user?.scope_code ?? null;
  return useApi(code && `centre:${code}`, async () => {
    if (!code) return null;
    const { data } = await api.GET("/centres/{code}", { params: { path: { code } } });
    return data ?? null;
  });
}
