import { expect, test } from "@playwright/test";

import {
  addChild,
  answerRemainingQuestions,
  completeAssessment,
  loginExistingParent,
  SHARED_PARENT_EMAIL,
} from "./helpers";

// Two complete 20-question UI assessments plus plan/follow-up persistence
// checks cannot reliably fit within Playwright's 30-second default.
test.setTimeout(90_000);

test("Case 10: weekly follow-up persists progress and replaces the active plan", async ({
  page,
  request,
}) => {
  const childName = "طفل متابعة أسبوعية";
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  const childId = await addChild(page, { name: childName, dateOfBirth: "2022-01-15" });

  // Initial assessment: weak start (all-never), followed by a real active plan.
  await completeAssessment(page, childId, "all-never");
  const firstAssessmentId = page.url().match(/\/assessments\/([^/]+)\/result$/)?.[1];
  expect(firstAssessmentId).toBeTruthy();
  const initialPlanResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith(`/api/v1/assessments/${firstAssessmentId}/weekly-plan`),
  );
  await page.getByRole("button", { name: "إنشاء الخطة الأسبوعية" }).click();
  const initialPlanResponse = await initialPlanResponsePromise;
  expect(initialPlanResponse.status()).toBe(201);
  const initialPlan = await initialPlanResponse.json();
  await expect(page).toHaveURL(/\/weekly-plan$/);
  expect(initialPlan.child_id).toBe(childId);
  expect(initialPlan.assessment_id).toBe(firstAssessmentId);

  // Open weekly follow-up through normal app navigation, not a direct URL.
  await page.getByRole("link", { name: "أطفالي", exact: true }).click();
  await page.getByRole("link", { name: new RegExp(childName) }).click();
  await page.getByRole("link", { name: "المتابعة الأسبوعية" }).click();
  await expect(page).toHaveURL(/\/reassessment/);
  const activePlanContext = page.getByTestId("active-weekly-plan-context");
  await expect(activePlanContext).toHaveAttribute("data-child-id", childId);
  await expect(activePlanContext).toHaveAttribute("data-plan-id", initialPlan.id);
  await expect(activePlanContext).toHaveAttribute(
    "data-assessment-id",
    firstAssessmentId as string,
  );
  await expect(page.getByText(`الطفل: ${childName}`)).toBeVisible();
  await expect(page.getByText(/الخطة النشطة منذ/)).toBeVisible();

  await page.getByRole("button", { name: "ابدأ أسئلة المتابعة الأسبوعية" }).click();
  await expect(page).toHaveURL(/\/assessments\/.+\/take/);
  await answerRemainingQuestions(page, "all-always");
  const secondAssessmentId = page.url().match(/\/assessments\/([^/]+)\/result$/)?.[1];
  expect(secondAssessmentId).toBeTruthy();
  expect(secondAssessmentId).not.toBe(firstAssessmentId);

  let followupSubmissionCount = 0;
  page.on("request", (outgoingRequest) => {
    if (
      outgoingRequest.method() === "POST" &&
      outgoingRequest.url().endsWith(`/api/v1/assessments/${secondAssessmentId}/followup`)
    ) {
      followupSubmissionCount += 1;
    }
  });
  const followupResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith(`/api/v1/assessments/${secondAssessmentId}/followup`),
  );
  const followupButton = page.getByRole("button", { name: "إكمال المتابعة الأسبوعية" });
  await followupButton.evaluate((button) => {
    const followupButtonElement = button as HTMLButtonElement;
    followupButtonElement.click();
    followupButtonElement.click();
  });
  const followupResponse = await followupResponsePromise;
  expect(followupResponse.status()).toBe(201);
  const followup = await followupResponse.json();
  expect(followup.child_id).toBe(childId);
  expect(followup.previous_assessment_id).toBe(firstAssessmentId);
  expect(followup.current_assessment_id).toBe(secondAssessmentId);
  expect(followupSubmissionCount).toBe(1);

  await expect(page).toHaveURL(/\/followups\/.+/);
  const followupUrl = page.url();
  await expect(page.getByText("نتيجة المتابعة الأسبوعية")).toBeVisible();
  await expect(page.getByText("النتيجة السابقة")).toBeVisible();
  await expect(page.getByText("النتيجة الحالية")).toBeVisible();
  await expect(page.getByText("نسبة التحسن")).toBeVisible();

  // The UI-authenticated request can verify persistence without another login.
  const authorization = followupResponse.request().headers()["authorization"];
  expect(authorization).toBeTruthy();
  const apiOrigin = new URL(followupResponse.url()).origin;
  const persistedFollowups = await request.get(
    `${apiOrigin}/api/v1/children/${childId}/followups`,
    { headers: { Authorization: authorization } },
  );
  expect(persistedFollowups.status()).toBe(200);
  const persistedFollowupRows = await persistedFollowups.json();
  expect(persistedFollowupRows).toHaveLength(1);
  expect(persistedFollowupRows[0].id).toBe(followup.id);

  // Follow-up detail remains available after a full reload.
  await page.reload();
  await expect(page).toHaveURL(followupUrl);
  await expect(page.getByText("نتيجة المتابعة الأسبوعية")).toBeVisible();
  await expect(page.getByText("نسبة التحسن")).toBeVisible();

  // Follow-up auto-regenerates and persists a different active weekly plan.
  const replacementPlanResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "GET" &&
      response.url().endsWith(`/api/v1/children/${childId}/weekly-plan`),
  );
  await page.getByRole("button", { name: "عرض الخطة الأسبوعية المحدّثة" }).click();
  const replacementPlanResponse = await replacementPlanResponsePromise;
  const replacementPlan = await replacementPlanResponse.json();
  await expect(page).toHaveURL(/\/weekly-plan$/);
  await expect(page.getByText("الخطة الأسبوعية")).toBeVisible();
  expect(replacementPlan.id).not.toBe(initialPlan.id);
  expect(replacementPlan.child_id).toBe(childId);
  expect(replacementPlan.assessment_id).toBe(secondAssessmentId);

  const reloadedPlanResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "GET" &&
      response.url().endsWith(`/api/v1/children/${childId}/weekly-plan`),
  );
  await page.reload();
  const reloadedPlanResponse = await reloadedPlanResponsePromise;
  const reloadedPlan = await reloadedPlanResponse.json();
  expect(reloadedPlan.id).toBe(replacementPlan.id);
  expect(reloadedPlan.assessment_id).toBe(secondAssessmentId);
});
