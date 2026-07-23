import { expect, test } from "@playwright/test";

import { loginExistingParent, registerNewParent, uniqueEmail } from "./helpers";

test("Case 1: register and login successfully", async ({ page }) => {
  const email = uniqueEmail("case01");

  await registerNewParent(page, { email });
  await expect(page.getByRole("heading", { name: /مرحبًا/ })).toBeVisible();

  // Log out, then log back in with the same credentials.
  await page.getByRole("button", { name: "تسجيل الخروج" }).click();
  await expect(page).toHaveURL(/\/login/);

  await loginExistingParent(page, email);
  await expect(page.getByRole("heading", { name: /مرحبًا/ })).toBeVisible();
});
