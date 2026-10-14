"use client";

import { useSession } from "@/components/shell/SessionProvider";

/** The district the signed-in planner plans for. */
export function useDistrictCode(): string {
  const { user } = useSession();
  if (!user) throw new Error("useDistrictCode needs a signed-in planner");
  return user.district_code;
}
