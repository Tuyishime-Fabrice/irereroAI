import { expect, test } from "@playwright/test";

import { watchErrors } from "./helpers";

test("a parent finds verified centres, and an empty search becomes a centre request", async ({
  page,
}) => {
  const errors = watchErrors(page);
  await page.goto("/find");

  await page.getByLabel("Sector").selectOption({ label: "Byumba" });
  await expect(page.getByText(/centres found/)).toBeVisible();
  await expect(page.getByText(/simulated data/i).first()).toBeVisible();

  await page.getByLabel("Sector").selectOption({ label: "Miyove" });
  await page.getByLabel("Distance").selectOption("2");
  await expect(page.getByText("No verified centre here yet")).toBeVisible();
  await page.getByRole("button", { name: "Request a centre here" }).click();
  await expect(page.getByText(/Your request was counted/)).toBeVisible();

  expect(errors).toEqual([]);
});
