import { expect, test } from "@playwright/test";

import { loginExistingParent, SHARED_PARENT_EMAIL } from "./helpers";

test.setTimeout(120_000);

test("70% reassessment eligibility, frozen AI-varied questions, افهم أكثر, and source disclosure", async ({
  page,
}) => {
  const loginResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" && response.url().endsWith("/api/v1/auth/login"),
  );
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  const loginResponse = await loginResponsePromise;
  const tokens = await loginResponse.json();
  const headers = { Authorization: `Bearer ${tokens.access_token}` };
  const apiOrigin = new URL(loginResponse.url()).origin;

  // Real deterministic assessment + plan, all-never so the referral/severity
  // is meaningfully non-trivial (regression check target below).
  const childResponse = await page.request.post(`${apiOrigin}/api/v1/children`, {
    headers,
    data: {
      name: "طفل مرحلة ثالثة",
      date_of_birth: "2022-08-15",
      gender: "female",
      home_language: "ar",
    },
  });
  expect(childResponse.status()).toBe(201);
  const child = await childResponse.json();

  const startResponse = await page.request.post(
    `${apiOrigin}/api/v1/children/${child.id}/assessments`,
    { headers },
  );
  const assessment = await startResponse.json();
  const questionsResponse = await page.request.get(
    `${apiOrigin}/api/v1/assessments/${assessment.id}/questions`,
    { headers },
  );
  const questions = await questionsResponse.json();
  await page.request.post(`${apiOrigin}/api/v1/assessments/${assessment.id}/answers`, {
    headers,
    data: {
      answers: questions.map((question: { id: string }) => ({
        question_id: question.id,
        response: "never",
      })),
    },
  });
  const completeResponse = await page.request.post(
    `${apiOrigin}/api/v1/assessments/${assessment.id}/complete`,
    { headers },
  );
  const completedAssessment = await completeResponse.json();
  const expectedSeverity = completedAssessment.overall_severity;
  const expectedReferral = completedAssessment.overall_referral;
  const expectedGoal = completedAssessment.priority_domains?.[0];

  const planResponse = await page.request.post(
    `${apiOrigin}/api/v1/assessments/${assessment.id}/weekly-plan`,
    { headers },
  );
  const plan = await planResponse.json();
  expect(plan.activities.length).toBe(14);

  // 1-2. Open the weekly plan through the real UI.
  await page.goto(`/children/${child.id}/weekly-plan`);
  await expect(page.getByRole("heading", { name: "الخطة الأسبوعية", exact: true })).toBeVisible();

  // 3. Below 70%: reassessment disabled with the required Arabic message.
  await expect(page.getByRole("button", { name: "إعادة التقييم الأسبوعي" })).toBeDisabled();
  await expect(
    page.getByText("يمكنك بدء إعادة التقييم بعد إكمال 70% من الأنشطة."),
  ).toBeVisible();

  // 4. Complete 10/14 (71.4%) — crosses the threshold without reaching 100%.
  for (const slot of plan.activities.slice(0, 10)) {
    const completion = await page.request.patch(
      `${apiOrigin}/api/v1/weekly-plan-activities/${slot.id}`,
      { headers, data: { completed: true } },
    );
    expect(completion.status()).toBe(200);
  }
  await page.reload();

  // 5. Confirm it becomes enabled.
  await expect(page.getByRole("heading", { name: "أصبحت إعادة التقييم متاحة" })).toBeVisible();
  const startLink = page.getByRole("link", { name: "بدء إعادة التقييم" });
  await expect(startLink).toBeVisible();

  // 6. Start reassessment.
  await startLink.click();
  await expect(page.getByRole("heading", { name: "المتابعة الأسبوعية" })).toBeVisible();
  await expect(
    page.getByText(
      "تمت صياغة الأسئلة بناءً على أنشطة الخطة الأسبوعية، بينما يعتمد حساب النتيجة على معايير المتابعة المعتمدة.",
    ),
  ).toBeVisible();

  // 7. Confirm 5-8 questions appear.
  const questionCards = page.getByTestId("kb06-weekly-question");
  const questionCount = await questionCards.count();
  expect(questionCount).toBeGreaterThanOrEqual(5);
  expect(questionCount).toBeLessThanOrEqual(8);
  const firstRoundWording = await questionCards.allTextContents();

  // 8. Reload and confirm the identical (frozen) questions.
  await page.reload();
  await expect(page.getByRole("heading", { name: "المتابعة الأسبوعية" })).toBeVisible();
  const secondRoundWording = await page.getByTestId("kb06-weekly-question").allTextContents();
  expect(secondRoundWording).toEqual(firstRoundWording);

  // Answer and submit, confirming deterministic facts survive the AI layer.
  const alwaysOptions = page.getByRole("radio", { name: "دائمًا" });
  const optionCount = await alwaysOptions.count();
  for (let i = 0; i < optionCount; i++) {
    await alwaysOptions.nth(i).click();
  }
  await page
    .getByRole("button", { name: "إرسال المتابعة وإنشاء خطة الأسبوع القادم" })
    .click();
  await expect(page.getByRole("heading", { name: "نتيجة المتابعة الأسبوعية" })).toBeVisible();

  // 9-10. Return to the (regenerated) weekly plan.
  await page.goto(`/children/${child.id}/weekly-plan`);
  await expect(page.getByRole("heading", { name: "الخطة الأسبوعية", exact: true })).toBeVisible();

  // 11-13. "افهم أكثر" on the first activity — assertions are scoped to
  // section headings unique to the explanation card (the plain activity
  // card above it also has "الهدف"/"خطوات التنفيذ" dt labels, so those two
  // are ambiguous across 14 activity cards and are intentionally not used).
  await page.getByRole("button", { name: "افهم أكثر" }).first().click();
  await expect(page.getByRole("heading", { name: /^افهم أكثر:/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "مثال حوار" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "إذا لم يستجب الطفل" })).toBeVisible();

  // 14-15. Expand the source disclosure, confirm readable label + secondary id.
  const sourceDisclosure = page.getByText(/المصادر المعتمدة \(\d+\)/).last();
  await sourceDisclosure.click();
  const disclosureDetails = sourceDisclosure.locator("xpath=ancestor::details[1]");
  await expect(disclosureDetails).toHaveAttribute("open", "");
  // No raw comma-separated source IDs as primary content anywhere on the page.
  await expect(page.getByText(/^المصادر المعتمدة: [A-Z]\d+/)).toHaveCount(0);

  // 16. Deterministic facts (scoring/severity/referral/activities) are
  // unchanged by the AI layer — confirm against the values captured before
  // any AI-assisted feature was touched.
  await page.goto(`/assessments/${assessment.id}/result`);
  await expect(page.getByText(expectedSeverity).first()).toBeVisible();
  if (expectedReferral && expectedReferral !== "لا") {
    await expect(page.getByRole("heading", { name: "توصية الإحالة إلى أخصائي" })).toBeVisible();
  }
  if (expectedGoal) {
    await expect(page.getByText(expectedGoal).first()).toBeVisible();
  }
});
