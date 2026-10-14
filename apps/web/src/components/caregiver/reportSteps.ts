import type { ReportBody } from "@/lib/offline/outbox";

export type CountField =
  | "enrolled_0_2_female"
  | "enrolled_0_2_male"
  | "enrolled_3_6_female"
  | "enrolled_3_6_male"
  | "avg_daily_attendance"
  | "waiting_list"
  | "caregivers_present"
  | "days_open"
  | "days_meal_served"
  | "referrals_growth_monitoring"
  | "children_with_disability";

export type Step =
  | { key: "week" }
  | { key: string; fields: CountField[]; max?: number }
  | { key: "water" }
  | { key: "problem" }
  | { key: "review" };

/** One question per step, in the order a caregiver thinks about the week. */
export const STEPS: Step[] = [
  { key: "week" },
  { key: "young", fields: ["enrolled_0_2_female", "enrolled_0_2_male"] },
  { key: "old", fields: ["enrolled_3_6_female", "enrolled_3_6_male"] },
  { key: "attendance", fields: ["avg_daily_attendance"] },
  { key: "days", fields: ["days_open", "days_meal_served"], max: 6 },
  { key: "caregivers", fields: ["caregivers_present"], max: 99 },
  { key: "waiting", fields: ["waiting_list"] },
  { key: "water" },
  { key: "health", fields: ["referrals_growth_monitoring", "children_with_disability"] },
  { key: "problem" },
  { key: "review" },
];

export const PROBLEMS = [
  "none",
  "no_food",
  "no_water",
  "caregiver_absent",
  "building_damage",
  "weather",
  "other",
] as const;

export function enrolled(body: ReportBody): number {
  return (
    body.enrolled_0_2_female +
    body.enrolled_0_2_male +
    body.enrolled_3_6_female +
    body.enrolled_3_6_male
  );
}

/** Problems that make a step impossible to accept, in the same terms as the server rules. */
export function stepProblem(step: Step, body: ReportBody): string | null {
  if (step.key === "attendance" && body.avg_daily_attendance > enrolled(body))
    return "attendance_above_enrolment";
  if (step.key === "days") {
    if (body.days_meal_served > body.days_open) return "meals_above_days_open";
    if (body.days_open === 0 && body.avg_daily_attendance > 0) return "attendance_while_closed";
  }
  if (step.key === "health" && body.children_with_disability > enrolled(body))
    return "disability_above_enrolment";
  return null;
}
