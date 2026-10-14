import { describe, expect, it } from "vitest";

import type { ReportBody } from "@/lib/offline/outbox";

import { STEPS, stepProblem } from "./reportSteps";

const body: ReportBody = {
  centre_code: "X",
  week_start: "2026-09-21",
  enrolled_0_2_female: 5,
  enrolled_0_2_male: 5,
  enrolled_3_6_female: 10,
  enrolled_3_6_male: 10,
  avg_daily_attendance: 25,
  waiting_list: 0,
  caregivers_present: 2,
  days_open: 5,
  days_meal_served: 5,
  wash_available: true,
  referrals_growth_monitoring: 0,
  children_with_disability: 1,
  main_problem: "none",
  channel: "web",
  confirmed: false,
};
const step = (key: string) => STEPS.find((s) => s.key === key)!;

describe("report steps", () => {
  it("has about ten questions before review", () => {
    expect(STEPS.length).toBe(11);
  });

  it("catches attendance above enrolment and meals above open days", () => {
    expect(stepProblem(step("attendance"), { ...body, avg_daily_attendance: 31 })).toBe(
      "attendance_above_enrolment",
    );
    expect(stepProblem(step("days"), { ...body, days_meal_served: 6 })).toBe(
      "meals_above_days_open",
    );
    expect(stepProblem(step("attendance"), body)).toBeNull();
  });
});
