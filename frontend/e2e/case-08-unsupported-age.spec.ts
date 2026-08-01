import { expect, test } from "@playwright/test";

import { addChild, loginExistingParent, SHARED_PARENT_EMAIL } from "./helpers";

test("Case 8: unsupported age (too young) hides assessment start and rejects it server-side", async ({
  page,
}) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  // DOB -> age 1, below the supported 2-5 range.
  const childId = await addChild(page, { name: "طفل عمره سنة", dateOfBirth: "2025-01-15" });

  await expect(page.getByText(/خارج النطاق المدعوم للتقييم/)).toBeVisible();
  await expect(page.getByRole("link", { name: "بدء تقييم" })).not.toBeVisible();

  // Navigating to the intro page directly and attempting to start still surfaces
  // the backend's real rejection, in Arabic — the frontend never fakes success.
  await page.goto(`/children/${childId}/assessment/intro`);
  await page.getByRole("button", { name: "ابدأ التقييم" }).click();
  await expect(page.getByText(/خارج النطاق المدعوم للتقييم/)).toBeVisible();
});

test("Case 8b: unsupported age (too old) hides assessment start", async ({ page }) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  // DOB -> age 6, above the supported 2-5 range.
  await addChild(page, { name: "طفل عمره ست سنوات", dateOfBirth: "2020-01-15" });

  await expect(page.getByText(/خارج النطاق المدعوم للتقييم/)).toBeVisible();
  await expect(page.getByRole("link", { name: "بدء تقييم" })).not.toBeVisible();
});
