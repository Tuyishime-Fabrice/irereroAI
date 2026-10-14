export type TourStep = {
  key: string;
  /** "planner" signs in as the demo planner first; "parent" is a public page; null stays put. */
  as: "planner" | "parent" | null;
  path: string;
  /** data-tour attribute of the element to highlight. */
  target: string;
};

/** The five-minute pitch, step by step. Runs on the seeded demo database, offline. */
export const TOUR: TourStep[] = [
  { key: "welcome", as: null, path: "/", target: "numbers" },
  { key: "needMap", as: "planner", path: "/district", target: "need-map" },
  { key: "reject", as: "planner", path: "/district/plan", target: "site-SITE-CYUMBA-V1" },
  { key: "whatIf", as: "planner", path: "/district/what-if", target: "what-if" },
  {
    key: "parent",
    as: "parent",
    path: "/request?sector=S-GICUMBI-CYUMBA",
    target: "request-centre",
  },
  { key: "promise", as: null, path: "/", target: "promise" },
];
