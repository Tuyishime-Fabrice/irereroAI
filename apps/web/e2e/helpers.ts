import { expect, type Page } from "@playwright/test";

export const roles = {
  caregiver: "Caregiver",
  sector_officer: "Sector ECD officer",
  district_planner: "District planner",
  national_analyst: "National analyst",
  admin: "System admin",
} as const;

/** Signs in through the demo accounts list, the way a judge would. */
export async function signInAs(page: Page, role: keyof typeof roles) {
  await page.goto("/sign-in");
  await page
    .getByRole("listitem")
    .filter({ has: page.getByText(roles[role], { exact: true }) })
    .getByRole("button", { name: "Use" })
    .click();
  await expect(page).not.toHaveURL(/sign-in/);
}

/** Fails the test on any uncaught error or console error. */
export function watchErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  return errors;
}
