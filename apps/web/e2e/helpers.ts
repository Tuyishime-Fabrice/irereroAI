import { expect, type Page } from "@playwright/test";

/** Signs in through the demo account on the sign-in page, the way a judge would. */
export async function signInAsPlanner(page: Page) {
  await page.goto("/sign-in");
  await page.getByRole("button", { name: "Use" }).click();
  await expect(page).toHaveURL(/\/district/);
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
