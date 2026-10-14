import { expect, test } from "@playwright/test";

import { signInAs, watchErrors } from "./helpers";

test("the planner rejects a suggestion and the plan re-runs without it", async ({ page }) => {
  const errors = watchErrors(page);
  await signInAs(page, "district_planner");
  await page.goto("/district/plan");
  await page.getByRole("button", { name: "Get suggestions" }).click();
  await expect(page.getByRole("heading", { name: "Shortlist" })).toBeVisible();

  const cyumba = page.locator("article", { hasText: "Cyumba village site A" });
  await expect(cyumba.getByText("Parents asked for a centre here", { exact: true })).toBeVisible();
  await cyumba.getByRole("button", { name: "Reject" }).click();
  await cyumba.getByLabel("No land available").check();
  await cyumba.getByRole("button", { name: "Reject suggestion" }).click();
  await expect(page.getByText("Rejected (1)")).toBeVisible();

  await page.goto("/district/decisions");
  await expect(page.getByText("Cyumba village site A").first()).toBeVisible();
  await expect(page.getByText("No land available").first()).toBeVisible();

  expect(errors).toEqual([]);
});
