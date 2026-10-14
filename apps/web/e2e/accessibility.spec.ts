import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { roles, signInAs } from "./helpers";

const pages: { path: string; role?: keyof typeof roles }[] = [
  { path: "/" },
  { path: "/find" },
  { path: "/methodology" },
  { path: "/sign-in" },
  { path: "/caregiver", role: "caregiver" },
  { path: "/caregiver/report", role: "caregiver" },
  { path: "/sector", role: "sector_officer" },
  { path: "/sector/alerts", role: "sector_officer" },
  { path: "/district", role: "district_planner" },
  { path: "/district/plan", role: "district_planner" },
  { path: "/find/ECD-GIC-001" },
  { path: "/tour" },
  { path: "/caregiver/sms", role: "caregiver" },
  { path: "/sector/centres", role: "sector_officer" },
  { path: "/sector/suggestions", role: "sector_officer" },
  { path: "/district/what-if", role: "district_planner" },
  { path: "/district/decisions", role: "district_planner" },
  { path: "/district/brief", role: "district_planner" },
  { path: "/national", role: "national_analyst" },
  { path: "/national/defaults", role: "national_analyst" },
  { path: "/national/status", role: "national_analyst" },
  { path: "/admin", role: "admin" },
  { path: "/admin/pipelines", role: "admin" },
  { path: "/admin/audit", role: "admin" },
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

for (const { path, role } of pages) {
  test(`no WCAG A/AA violations on ${path}`, async ({ page }) => {
    if (role) await signInAs(page, role);
    await page.goto(path);
    await expectNoViolations(page);
  });
}

const kinyarwanda = ["/", "/find", "/caregiver/report", "/district/plan"];

for (const { path, role } of pages.filter((p) => kinyarwanda.includes(p.path))) {
  test(`no WCAG A/AA violations on ${path} in Kinyarwanda`, async ({ page, context, baseURL }) => {
    if (role) await signInAs(page, role);
    await context.addCookies([{ name: "irerero_locale", value: "rw", url: baseURL ?? "" }]);
    await page.goto(path);
    await expect(page.locator("html")).toHaveAttribute("lang", "rw");
    await expectNoViolations(page);
  });
}
