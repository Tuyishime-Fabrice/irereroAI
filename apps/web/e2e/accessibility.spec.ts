import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { signInAsPlanner } from "./helpers";

const pages: { path: string; planner?: boolean }[] = [
  { path: "/" },
  { path: "/request" },
  { path: "/methodology" },
  { path: "/sign-in" },
  { path: "/tour" },
  { path: "/district", planner: true },
  { path: "/district/plan", planner: true },
  { path: "/district/what-if", planner: true },
  { path: "/district/decisions", planner: true },
  { path: "/district/brief", planner: true },
  { path: "/national", planner: true },
];

async function expectNoViolations(page: Page) {
  await page.waitForLoadState("networkidle");
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    // The map canvas is decorative here; every map has a table alternative.
    .exclude(".maplibregl-canvas")
    .analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.length} × ${v.help}`)).toEqual([]);
}

for (const { path, planner } of pages) {
  test(`no WCAG A/AA violations on ${path}`, async ({ page }) => {
    if (planner) await signInAsPlanner(page);
    await page.goto(path);
    await expectNoViolations(page);
  });
}

const kinyarwanda = ["/", "/request", "/district/plan"];

for (const { path, planner } of pages.filter((p) => kinyarwanda.includes(p.path))) {
  test(`no WCAG A/AA violations on ${path} in Kinyarwanda`, async ({ page, context, baseURL }) => {
    if (planner) await signInAsPlanner(page);
    await context.addCookies([{ name: "irerero_locale", value: "rw", url: baseURL ?? "" }]);
    await page.goto(path);
    await expect(page.locator("html")).toHaveAttribute("lang", "rw");
    await expectNoViolations(page);
  });
}
