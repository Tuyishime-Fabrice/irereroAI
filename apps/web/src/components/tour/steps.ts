import type { Schemas } from "@/lib/api/client";

export type TourStep = {
  key: string;
  /** Demo account to switch to, or null to stay as you are. */
  role: Schemas["Role"] | null;
  path: string;
  /** data-tour attribute of the element to highlight. */
  target: string;
};

/** The five-minute pitch, step by step. Runs on the seeded demo database, offline. */
export const TOUR: TourStep[] = [
  { key: "welcome", role: null, path: "/", target: "numbers" },
  { key: "needMap", role: "district_planner", path: "/district", target: "need-map" },
  {
    key: "reject",
    role: "district_planner",
    path: "/district/plan",
    target: "site-SITE-CYUMBA-V1",
  },
  { key: "caregiver", role: "caregiver", path: "/caregiver", target: "start-report" },
  { key: "alert", role: "sector_officer", path: "/sector/alerts", target: "alert-list" },
  {
    key: "parent",
    role: "parent",
    path: "/find?sector=S-GICUMBI-MIYOVE&radius=2",
    target: "request-centre",
  },
  { key: "replay", role: "district_planner", path: "/district", target: "week-scrubber" },
  { key: "promise", role: null, path: "/", target: "promise" },
];
