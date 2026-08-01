import { expect, test } from "@playwright/test";

import { addChild, completeAssessment, loginExistingParent, SHARED_PARENT_EMAIL } from "./helpers";

test("Case 5: three-year-old child completes a full assessment", async ({ page }) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  const childId = await addChild(page, { name: "طفل عمره ثلاث سنوات", dateOfBirth: "2023-01-15" });

  await completeAssessment(page, childId, "all-always");

  await expect(page.getByText("النتيجة الكلية")).toBeVisible();
});

test("Case 6: four-year-old child completes a full assessment", async ({ page }) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  const childId = await addChild(page, { name: "طفل عمره أربع سنوات", dateOfBirth: "2022-01-15" });

  await completeAssessment(page, childId, "all-always");

  await expect(page.getByText("النتيجة الكلية")).toBeVisible();
});

test("Case 7: five-year-old child completes a full assessment", async ({ page }) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  const childId = await addChild(page, { name: "طفل عمره خمس سنوات", dateOfBirth: "2021-01-15" });

  await completeAssessment(page, childId, "all-always");

  await expect(page.getByText("النتيجة الكلية")).toBeVisible();
});
