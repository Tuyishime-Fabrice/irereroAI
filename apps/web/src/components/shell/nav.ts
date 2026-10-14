export type NavItem = { href: string; key: string };

export const HOME = "/district";

/** The planner's rail. Pages are guarded by the API; this only arranges them. */
export const NAV: NavItem[] = [
  { href: "/district", key: "needMap" },
  { href: "/district/plan", key: "plan" },
  { href: "/district/what-if", key: "whatIf" },
  { href: "/national", key: "national" },
  { href: "/district/decisions", key: "decisions" },
];
