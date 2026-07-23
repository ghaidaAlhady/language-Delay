import { expect, test } from "@playwright/test";

import { addChild, completeAssessment, loginExistingParent, SHARED_PARENT_EMAIL } from "./helpers";

test("Case 4: all-No (never) assessment surfaces a delay severity and referral guidance", async ({ page }) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  const childId = await addChild(page, { name: "طفل تقييم سلبي", dateOfBirth: "2022-01-15" });

  await completeAssessment(page, childId, "all-never");

  await expect(page.getByText("النتيجة الكلية")).toBeVisible();
  await expect(page.getByText("تأخر ملحوظ").first()).toBeVisible();
  await expect(page.getByText("توصية الإحالة إلى أخصائي")).toBeVisible();
});
