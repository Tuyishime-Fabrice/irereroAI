"use client";

import { useSession } from "@/components/shell/SessionProvider";
import { useWorkspace } from "@/components/shell/Workspace";

const DEMO_DISTRICT = "D-GICUMBI";

/** The district being planned: the planner's own, or the one a national user picked. */
export function useDistrictCode(): string {
  const { user } = useSession();
  const { area } = useWorkspace();
  if (user?.scope_level === "district" && user.scope_code) return user.scope_code;
  return area?.startsWith("D-") ? area : DEMO_DISTRICT;
}
