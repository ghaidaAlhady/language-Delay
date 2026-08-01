import { expect, test } from "@playwright/test";

import { loginExistingParent, SHARED_PARENT_EMAIL } from "./helpers";

test("protected routes redirect an unauthenticated visitor to /login", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
});

test("a session survives a full page refresh (silent token refresh on load)", async ({ page }) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  await expect(page.getByRole("heading", { name: /مرحبًا/ })).toBeVisible();

  await page.reload();
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByRole("heading", { name: /مرحبًا/ })).toBeVisible();
});

test("an invalid/expired refresh token redirects to login instead of showing a broken page", async ({
  page,
}) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  await expect(page.getByRole("heading", { name: /مرحبًا/ })).toBeVisible();

  // Simulate returning with a refresh token the backend no longer recognizes.
  await page.evaluate(() => sessionStorage.setItem("sg_refresh_token", "clearly-invalid-token"));
  await page.reload();

  await expect(page).toHaveURL(/\/login/);
});

test("logging out clears the session and re-protects previously accessible pages", async ({ page }) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  await page.getByRole("button", { name: "تسجيل الخروج" }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
});

test("an offline network condition shows the Arabic offline message, not a crash", async ({ page, context }) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  // Load the page and its assets while online; only the *submit* happens offline,
  // matching how a real user would lose connectivity mid-session (client-side
  // routing doesn't need the network, only the API call does).
  await page.goto("/children/new");
  await page.getByLabel("اسم الطفل").fill("طفل بلا اتصال");
  await page.getByLabel("تاريخ الميلاد").fill("2022-01-15");
  await page.getByLabel("الجنس").selectOption("female");
  await page.getByLabel("لغة المنزل").fill("ar");

  await context.setOffline(true);
  await page.getByRole("button", { name: "حفظ" }).click();

  // Some browser/network stacks fail an offline fetch immediately; others
  // leave it hanging until our client-side request timeout (15s) fires.
  // Either way the app must show the offline message, so allow enough time
  // for the slow path too.
  await expect(page.getByRole("alert")).toContainText("غير متصل بالإنترنت", { timeout: 20_000 });
  await context.setOffline(false);
});

test("a 500 server error shows a safe Arabic message with no stack trace or technical details", async ({
  page,
}) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  await page.route("**/api/v1/children", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "internal_error", message: "boom" } }),
      });
    }
    return route.continue();
  });

  await page.goto("/children");
  await expect(page.getByRole("alert")).toContainText("حدث خطأ في الخادم");
  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toContain("Traceback");
  expect(bodyText).not.toContain("boom");
  expect(bodyText.toLowerCase()).not.toContain("exception");
});
