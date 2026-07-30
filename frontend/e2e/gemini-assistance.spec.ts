import { expect, type Page, test } from "@playwright/test";

import { loginExistingParent, SHARED_PARENT_EMAIL } from "./helpers";

test.setTimeout(120_000);

interface JourneyResources {
  assessmentId: string;
  childId: string;
  planId: string;
}

async function createAssessmentAndPlan(
  page: Page,
  apiOrigin: string,
  authorization: string,
  responseValue: "always" | "never",
): Promise<JourneyResources> {
  const headers = { Authorization: authorization };
  const childResponse = await page.request.post(`${apiOrigin}/api/v1/children`, {
    headers,
    data: {
      name: `طفل صياغة ${responseValue}`,
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
  expect(startResponse.status()).toBe(201);
  const assessment = await startResponse.json();

  const questionsResponse = await page.request.get(
    `${apiOrigin}/api/v1/assessments/${assessment.id}/questions`,
    { headers },
  );
  expect(questionsResponse.status()).toBe(200);
  const questions = await questionsResponse.json();
  const answersResponse = await page.request.post(
    `${apiOrigin}/api/v1/assessments/${assessment.id}/answers`,
    {
      headers,
      data: {
        answers: questions.map((question: { id: string }) => ({
          question_id: question.id,
          response: responseValue,
        })),
      },
    },
  );
  expect(answersResponse.status()).toBe(200);
  const completeResponse = await page.request.post(
    `${apiOrigin}/api/v1/assessments/${assessment.id}/complete`,
    { headers },
  );
  expect(completeResponse.status()).toBe(200);

  const planResponse = await page.request.post(
    `${apiOrigin}/api/v1/assessments/${assessment.id}/weekly-plan`,
    { headers },
  );
  expect(planResponse.status()).toBe(201);
  const plan = await planResponse.json();
  return {
    assessmentId: assessment.id,
    childId: child.id,
    planId: plan.id,
  };
}

test("safe fake Gemini covers three assisted surfaces and deterministic fallback", async ({
  page,
}) => {
  const loginResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" && response.url().endsWith("/api/v1/auth/login"),
  );
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  const loginResponse = await loginResponsePromise;
  const tokens = await loginResponse.json();
  const authorization = `Bearer ${tokens.access_token}`;
  const apiOrigin = new URL(loginResponse.url()).origin;

  const notable = await createAssessmentAndPlan(page, apiOrigin, authorization, "never");

  await page.goto(`/assessments/${notable.assessmentId}/result`);
  await expect(page.getByRole("heading", { name: "النتيجة الكلية" })).toBeVisible();
  await expect(page.getByText("صياغة مساندة بالذكاء الاصطناعي")).toBeVisible();
  await expect(page.getByRole("heading", { name: "شرح مبسط للنتيجة" })).toBeVisible();

  await page.goto(`/children/${notable.childId}/weekly-plan`);
  await expect(page.getByRole("heading", { name: "الخطة الأسبوعية", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "ملخص الخطة الأسبوعية" })).toBeVisible();
  await expect(page.getByText("صياغة مساندة بالذكاء الاصطناعي")).toBeVisible();

  const headers = { Authorization: authorization };
  const planResponse = await page.request.get(
    `${apiOrigin}/api/v1/children/${notable.childId}/weekly-plan`,
    { headers },
  );
  const plan = await planResponse.json();
  for (const slot of plan.activities) {
    const completion = await page.request.patch(
      `${apiOrigin}/api/v1/weekly-plan-activities/${slot.id}`,
      { headers, data: { completed: true } },
    );
    expect(completion.status()).toBe(200);
  }
  const questionsResponse = await page.request.get(
    `${apiOrigin}/api/v1/weekly-plans/${notable.planId}/followup-questions`,
    { headers },
  );
  expect(questionsResponse.status()).toBe(200);
  const context = await questionsResponse.json();
  const followupResponse = await page.request.post(
    `${apiOrigin}/api/v1/weekly-plans/${notable.planId}/followup`,
    {
      headers,
      data: {
        answers: context.questions.map((question: { id: string }) => ({
          question_id: question.id,
          response: "always",
        })),
      },
    },
  );
  expect(followupResponse.status()).toBe(201);
  const followup = await followupResponse.json();

  await page.goto(`/followups/${followup.id}`);
  await expect(page.getByRole("heading", { name: "نتيجة المتابعة الأسبوعية" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "ملخص تقدم الأسبوع" })).toBeVisible();
  await expect(page.getByText("صياغة مساندة بالذكاء الاصطناعي")).toBeVisible();

  const normal = await createAssessmentAndPlan(page, apiOrigin, authorization, "always");
  await page.goto(`/assessments/${normal.assessmentId}/result`);
  await expect(page.getByText("ملخص آمن من النظام")).toBeVisible();
  await expect(
    page.getByText("لم تتوفر صياغة الذكاء الاصطناعي، لذا نعرض ملخصاً حتمياً آمناً."),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "النتيجة الكلية" })).toBeVisible();
});
