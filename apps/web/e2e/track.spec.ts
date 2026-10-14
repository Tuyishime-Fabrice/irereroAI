import { expect, test } from "@playwright/test";

import { signInAs, watchErrors } from "./helpers";

test.describe("track", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("a caregiver sends this week's report from a phone", async ({ page }) => {
    const errors = watchErrors(page);
    await signInAs(page, "caregiver");
    await expect(page.getByText("This week's report is not in yet.")).toBeVisible();

    await page.getByRole("link", { name: "Start this week's report" }).click();
    await expect(page.getByText("Which week are you reporting?")).toBeVisible();
    for (let step = 0; step < 9; step++) await page.getByRole("button", { name: "Next" }).click();
    await expect(page.getByText("What was the main problem this week?")).toBeVisible();
    await page.getByLabel("No water").check();
    await page.getByRole("button", { name: "Next" }).click();
    await expect(page.getByText("The numbers look right.")).toBeVisible();
    await page.getByRole("button", { name: "Send report" }).click();
    await expect(page.getByText("Report sent")).toBeVisible();

    expect(errors).toEqual([]);
  });
});

test("the sector officer acknowledges and resolves an alert", async ({ page }) => {
  const errors = watchErrors(page);
  await signInAs(page, "sector_officer");
  await page.goto("/sector/alerts");
  const alert = page.locator('[data-tour="alert-list"]').getByRole("link").first();
  await alert.click();
  await expect(page.getByText("Follow up")).toBeVisible();

  await page.getByRole("button", { name: "Acknowledge" }).click();
  await expect(page.getByText("Acknowledged").first()).toBeVisible();
  await page
    .getByLabel("What was done?")
    .fill("Visited the centre and agreed a plan with the caregiver.");
  await page.getByRole("button", { name: "Mark as resolved" }).click();
  await expect(page.getByText(/Resolved: Visited the centre/)).toBeVisible();

  expect(errors).toEqual([]);
});
