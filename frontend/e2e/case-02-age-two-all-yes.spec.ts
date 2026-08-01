import { expect, test } from "@playwright/test";

import { addChild, completeAssessment, loginExistingParent, SHARED_PARENT_EMAIL } from "./helpers";

test("Case 2: two-year-old child with an all-Yes (always) assessment scores fully normal", async ({ page }) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  const childId = await addChild(page, { name: "طفل عمره سنتان", dateOfBirth: "2024-01-15" });

  await completeAssessment(page, childId, "all-always");

  await expect(page.getByText("طبيعي").first()).toBeVisible();
  await expect(page.getByText(/درجة الثقة/)).toHaveCount(0);
  await expect(
    page.getByText("المتابعة: إعادة التقييم بعد أسبوع وتحديث الخطة").first(),
  ).toBeVisible();
});
