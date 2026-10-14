import type { Schemas } from "@/lib/api/client";

export type NavItem = { href: string; key: string };

/** The left rail per role. Pages also check roles; the API is the real guard. */
export const NAV: Record<Schemas["Role"], NavItem[]> = {
  parent: [
    { href: "/find", key: "find" },
    { href: "/account", key: "account" },
  ],
  caregiver: [
    { href: "/caregiver", key: "home" },
    { href: "/caregiver/report", key: "report" },
    { href: "/caregiver/sms", key: "sms" },
  ],
  sector_officer: [
    { href: "/sector", key: "overview" },
    { href: "/sector/alerts", key: "alerts" },
    { href: "/sector/centres", key: "centres" },
    { href: "/sector/suggestions", key: "suggestions" },
  ],
  district_planner: [
    { href: "/district", key: "needMap" },
    { href: "/district/plan", key: "plan" },
    { href: "/district/what-if", key: "whatIf" },
    { href: "/district/decisions", key: "decisions" },
  ],
  national_analyst: [
    { href: "/national", key: "nationalMap" },
    { href: "/national/defaults", key: "defaults" },
    { href: "/national/status", key: "status" },
  ],
  admin: [
    { href: "/admin", key: "users" },
    { href: "/admin/pipelines", key: "pipelines" },
    { href: "/admin/audit", key: "audit" },
    { href: "/national/status", key: "models" },
  ],
};
