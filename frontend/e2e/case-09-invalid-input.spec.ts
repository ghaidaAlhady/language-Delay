import { expect, test } from "@playwright/test";

import { addChild, loginExistingParent, SHARED_PARENT_EMAIL } from "./helpers";

test("Case 9: empty registration form shows Arabic validation errors and does not submit", async ({ page }) => {
  await page.goto("/register");
  await page.getByRole("button", { name: "إنشاء حساب" }).click();

  await expect(page.getByText("الاسم مطلوب.")).toBeVisible();
  await expect(page.getByText("البريد الإلكتروني مطلوب.")).toBeVisible();
  await expect(page).toHaveURL(/\/register/);
});

test("Case 9: mismatched password confirmation blocks registration", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("الاسم").fill("ولي أمر");
  await page.getByLabel("البريد الإلكتروني").fill("someone@example.com");
  await page.getByLabel("كلمة المرور", { exact: true }).fill("supersecret1");
  await page.getByLabel("تأكيد كلمة المرور").fill("different1");
  await page.getByRole("button", { name: "إنشاء حساب" }).click();

  await expect(page.getByText("كلمتا المرور غير متطابقتين.")).toBeVisible();
  await expect(page).toHaveURL(/\/register/);
});

test("Case 9: malformed email blocks login", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("البريد الإلكتروني").fill("not-an-email");
  await page.getByLabel("كلمة المرور").fill("supersecret1");
  await page.getByRole("button", { name: "تسجيل الدخول" }).click();

  await expect(page.getByText("صيغة البريد الإلكتروني غير صحيحة.")).toBeVisible();
  await expect(page).toHaveURL(/\/login/);
});

test.describe("authenticated invalid-input cases", () => {
  test("Case 9: empty child form shows Arabic validation errors and does not submit", async ({ page }) => {
    await loginExistingParent(page, SHARED_PARENT_EMAIL);
    await page.goto("/children/new");
    await page.getByRole("button", { name: "حفظ" }).click();

    await expect(page.getByText("اسم الطفل مطلوب.")).toBeVisible();
    await expect(page).toHaveURL(/\/children\/new/);
  });

  test("Case 9: an unanswered assessment question blocks progression (cannot submit incomplete)", async ({
    page,
  }) => {
    await loginExistingParent(page, SHARED_PARENT_EMAIL);
    const childId = await addChild(page, { name: "طفل تقييم غير مكتمل", dateOfBirth: "2022-01-15" });

    await page.goto(`/children/${childId}/assessment/intro`);
    await page.getByRole("button", { name: "ابدأ التقييم" }).click();
    await expect(page).toHaveURL(/\/assessments\/.+\/take/);

    // The UI architecturally cannot submit an assessment early — Next/Finish
    // stays disabled until a response is selected for the current question,
    // and completion is only ever invoked after the last question. This is
    // what actually prevents incomplete submission from this client. The
    // resulting "missing_question_ids" 400 + Arabic message
    // (getMissingQuestionCount/errorMessages "assessment-complete") is unit
    // tested directly in src/utils/errorMessages.test.ts.
    await expect(page.getByRole("button", { name: "التالي" })).toBeDisabled();
  });
});
