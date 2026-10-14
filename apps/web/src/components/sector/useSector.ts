"use client";

import { useSession } from "@/components/shell/SessionProvider";
import { useWorkspace } from "@/components/shell/Workspace";
import { api } from "@/lib/api/client";
import { useApi } from "@/lib/useApi";

/** The sector in view: the officer's own, or the one an admin picked. */
export function useSectorCode(): string | null {
  const { user } = useSession();
  const { area } = useWorkspace();
  return user?.scope_level === "sector" ? (user.scope_code ?? null) : area;
}

export function useCentres(area: string | null) {
  const { week } = useWorkspace();
  return useApi(area && `centres:${area}:${week}`, async () => {
    if (!area) return null;
    const { data } = await api.GET("/centres", { params: { query: { area, week } } });
    return data ?? null;
  });
}

export function useAlerts(area: string | null) {
  const { week } = useWorkspace();
  return useApi(area && `alerts:${area}:${week}`, async () => {
    if (!area) return null;
    const { data } = await api.GET("/alerts", { params: { query: { area, as_of: week } } });
    return data ?? null;
  });
}
