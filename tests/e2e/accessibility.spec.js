const { test, expect } = require("@playwright/test");
const AxeBuilder = require("@axe-core/playwright").default;

for (const [name, path] of [
  ["landing", "/"],
  ["login", "/account/login/"],
  ["registration", "/account/register/"],
  ["password reset", "/account/password-reset/"],
  ["privacy", "/privacy/"],
]) {
  test(`${name} has no serious accessibility violations`, async ({ page }) => {
    await page.goto(path);
    await expect(page.locator("main")).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const serious = results.violations.filter(({ impact }) =>
      ["critical", "serious"].includes(impact)
    );
    expect(serious).toEqual([]);
  });
}

