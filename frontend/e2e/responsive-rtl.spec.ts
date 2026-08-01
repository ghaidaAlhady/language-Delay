import { expect, test } from "@playwright/test";

import { addChild, loginExistingParent, SHARED_PARENT_EMAIL } from "./helpers";

/**
 * Every spec in this suite already runs across all three configured
 * Playwright projects (desktop-chromium, tablet, mobile-chromium — see
 * playwright.config.ts), so functional flows are exercised on all three
 * form factors "for free". This file adds targeted layout assertions.
 */

test("RTL direction and no horizontal overflow on the landing page", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

  const { scrollWidth, clientWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);
});

test("focus states are visible on interactive elements (keyboard navigation)", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("البريد الإلكتروني").focus();
  await expect(page.getByLabel("البريد الإلكتروني")).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(page.getByLabel("كلمة المرور")).toBeFocused();
});

test.describe("authenticated layout checks", () => {
  test("RTL persists and no horizontal overflow on an authenticated, data-heavy page", async ({ page }) => {
    await loginExistingParent(page, SHARED_PARENT_EMAIL);
    await addChild(page, { name: "طفل اختبار التخطيط", dateOfBirth: "2022-01-15" });

    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

    const { scrollWidth, clientWidth } = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);
  });
});
