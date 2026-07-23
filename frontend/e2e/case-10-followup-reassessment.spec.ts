import { expect, test } from "@playwright/test";

import {
  addChild,
  answerRemainingQuestions,
  completeAssessment,
  loginExistingParent,
  SHARED_PARENT_EMAIL,
} from "./helpers";

test("Case 10: weekly follow-up and reassessment compares against the previous assessment", async ({
  page,
}) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  const childId = await addChild(page, { name: "طفل متابعة أسبوعية", dateOfBirth: "2022-01-15" });

  // First assessment: weak start (all-never) so the second, stronger assessment shows improvement.
  await completeAssessment(page, childId, "all-never");
  await page.getByRole("button", { name: "إنشاء الخطة الأسبوعية" }).click();
  await expect(page).toHaveURL(/\/weekly-plan$/);

  // Reassessment, from the child detail hub.
  await page.goto(`/children/${childId}`);
  await page.getByRole("link", { name: "إعادة التقييم" }).click();
  await expect(page).toHaveURL(/\/reassessment/);
  await page.getByRole("button", { name: "ابدأ إعادة التقييم" }).click();
  await expect(page).toHaveURL(/\/assessments\/.+\/take/);

  await answerRemainingQuestions(page, "all-always");

  await page.getByRole("button", { name: "مقارنة بالتقييم السابق" }).click();
  await expect(page).toHaveURL(/\/followups\/.+/);
  await expect(page.getByText("نتيجة المتابعة الأسبوعية")).toBeVisible();
  await expect(page.getByText("النتيجة السابقة")).toBeVisible();
  await expect(page.getByText("النتيجة الحالية")).toBeVisible();
  await expect(page.getByText("نسبة التحسن")).toBeVisible();

  // Follow-up auto-regenerates the weekly plan.
  await page.getByRole("button", { name: "عرض الخطة الأسبوعية المحدّثة" }).click();
  await expect(page).toHaveURL(/\/weekly-plan$/);
  await expect(page.getByText("الخطة الأسبوعية")).toBeVisible();
});
