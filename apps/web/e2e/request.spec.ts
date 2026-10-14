import { expect, test } from "@playwright/test";

import { watchErrors } from "./helpers";

test("a parent sees the nearest centres and requests one closer", async ({ page }) => {
  const errors = watchErrors(page);
  await page.goto("/request");
  await page.getByLabel("Sector").selectOption({ label: "Cyumba" });
  await expect(page.getByRole("heading", { name: "Nearest verified centres" })).toBeVisible();
  await expect(page.getByText(/min walk/).first()).toBeVisible();
  await expect(page.getByText(/simulated data/i).first()).toBeVisible();

  await page.getByLabel("Age of the child").selectOption("3_6");
  await page.getByRole("button", { name: "Request a centre here" }).click();
  await expect(page.getByText(/Your request was counted/)).toBeVisible();

  expect(errors).toEqual([]);
});
