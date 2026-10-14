import type { Schemas } from "@/lib/api/client";

type Role = Schemas["Role"];

/** Where each role lands after signing in. */
export function homeFor(role: Role): string {
  return {
    parent: "/find",
    caregiver: "/caregiver",
    sector_officer: "/sector",
    district_planner: "/district",
    national_analyst: "/national",
    admin: "/admin",
  }[role];
}
