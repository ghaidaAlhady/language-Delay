import { expect, test } from "@playwright/test";

import {
  addChild,
  completeAssessment,
  loginExistingParent,
  SHARED_PARENT_EMAIL,
} from "./helpers";

test.setTimeout(120_000);

test("Case 10: completed plan opens KB06 follow-up once and activates a persistent replacement", async ({
  page,
  request,
}) => {
  const childName = "طفل متابعة أسبوعية";
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  const childId = await addChild(page, {
    name: childName,
    dateOfBirth: "2022-01-15",
  });

  await completeAssessment(page, childId, "all-never");
  const assessmentId = page.url().match(/\/assessments\/([^/]+)\/result$/)?.[1];
  expect(assessmentId).toBeTruthy();
  const initialPlanResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response
        .url()
        .endsWith(`/api/v1/assessments/${assessmentId}/weekly-plan`),
  );
  await page.getByRole("button", { name: "إنشاء الخطة الأسبوعية" }).click();
  const initialPlanResponse = await initialPlanResponsePromise;
  expect(initialPlanResponse.status()).toBe(201);
  const initialPlan = await initialPlanResponse.json();
  await expect(page).toHaveURL(/\/weekly-plan$/);

  // Complete each persisted activity through the real UI.
  for (let index = 0; index < initialPlan.total_activities; index += 1) {
    const completionResponse = page.waitForResponse(
      (response) =>
        response.request().method() === "PATCH" &&
        response.url().includes("/api/v1/weekly-plan-activities/"),
    );
    await page
      .getByRole("button", { name: "تم", exact: true })
      .first()
      .click();
    const response = await completionResponse;
    expect(response.status()).toBe(200);
    const persistedPlan = await response.json();
    expect(persistedPlan.completed_count).toBe(index + 1);
    await expect(
      page.getByRole("button", { name: "مكتمل", exact: true }),
    ).toHaveCount(index + 1);
  }

  await expect(page.getByRole("heading", { name: "أصبحت إعادة التقييم متاحة" })).toBeVisible();
  await expect(
    page.getByText("أكملتِ 14 من 14 نشاطًا — أصبحت إعادة التقييم متاحة."),
  ).toBeVisible();
  const followupCta = page.getByRole("link", {
    name: "بدء إعادة التقييم",
  });
  await expect(followupCta).toHaveAttribute(
    "href",
    `/children/${childId}/reassessment?planId=${initialPlan.id}`,
  );

  // Completion and CTA survive a full reload.
  await page.reload();
  await expect(page.getByText("الإنجاز — 14 من 14")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "بدء إعادة التقييم" }),
  ).toBeVisible();

  // Open through normal navigation and verify exact child/plan context.
  await page.getByRole("link", { name: "بدء إعادة التقييم" }).click();
  await expect(page).toHaveURL(
    new RegExp(`/children/${childId}/reassessment\\?planId=${initialPlan.id}`),
  );
  const activePlanContext = page.getByTestId("active-weekly-plan-context");
  await expect(activePlanContext).toHaveAttribute("data-child-id", childId);
  await expect(activePlanContext).toHaveAttribute(
    "data-plan-id",
    initialPlan.id,
  );
  await expect(activePlanContext).toHaveAttribute(
    "data-assessment-id",
    assessmentId as string,
  );
  await expect(page.getByText(`الطفل: ${childName}`)).toBeVisible();

  const weeklyQuestions = page.getByTestId("kb06-weekly-question");
  const questionCount = await weeklyQuestions.count();
  expect(questionCount).toBeGreaterThanOrEqual(5);
  expect(questionCount).toBeLessThanOrEqual(8);
  for (let index = 0; index < questionCount; index += 1) {
    await expect(weeklyQuestions.nth(index)).toHaveAttribute(
      "data-source-file",
      "KB06.json",
    );
  }
  await expect(
    page.getByText("هل يستجيب الطفل عند مناداة اسمه؟"),
  ).toHaveCount(0);

  for (const alwaysOption of await page
    .getByRole("radio", { name: "دائمًا" })
    .all()) {
    await alwaysOption.click();
  }

  let followupSubmissionCount = 0;
  page.on("request", (outgoingRequest) => {
    if (
      outgoingRequest.method() === "POST" &&
      outgoingRequest
        .url()
        .endsWith(`/api/v1/weekly-plans/${initialPlan.id}/followup`)
    ) {
      followupSubmissionCount += 1;
    }
  });
  const followupResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response
        .url()
        .endsWith(`/api/v1/weekly-plans/${initialPlan.id}/followup`),
  );
  const submitButton = page.getByRole("button", {
    name: "إرسال المتابعة وإنشاء خطة الأسبوع القادم",
  });
  await submitButton.evaluate((button) => {
    const element = button as HTMLButtonElement;
    element.click();
    element.click();
  });
  const followupResponse = await followupResponsePromise;
  expect(followupResponse.status()).toBe(201);
  const followup = await followupResponse.json();
  expect(followup.child_id).toBe(childId);
  expect(followup.weekly_plan_id).toBe(initialPlan.id);
  expect(followup.previous_assessment_id).toBe(assessmentId);
  expect(followup.current_assessment_id).toBeNull();
  expect(followupSubmissionCount).toBe(1);

  await expect(page).toHaveURL(/\/followups\/.+/);
  const followupUrl = page.url();
  await expect(page.getByText("نتيجة المتابعة الأسبوعية")).toBeVisible();
  await expect(page.getByText("إنجاز أنشطة الخطة")).toBeVisible();
  await expect(page.getByText("تحقق المهارات المستهدفة")).toBeVisible();
  await expect(page.getByText("مؤشر التقدم الأسبوعي")).toBeVisible();

  const authorization = followupResponse.request().headers()["authorization"];
  expect(authorization).toBeTruthy();
  const apiOrigin = new URL(followupResponse.url()).origin;
  const persistedFollowups = await request.get(
    `${apiOrigin}/api/v1/children/${childId}/followups`,
    { headers: { Authorization: authorization } },
  );
  expect(persistedFollowups.status()).toBe(200);
  const persistedRows = await persistedFollowups.json();
  expect(persistedRows).toHaveLength(1);
  expect(persistedRows[0].id).toBe(followup.id);

  await page.reload();
  await expect(page).toHaveURL(followupUrl);
  await expect(page.getByText("مؤشر التقدم الأسبوعي")).toBeVisible();

  const replacementPlanResponsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "GET" &&
      response.url().endsWith(`/api/v1/children/${childId}/weekly-plan`),
  );
  await page
    .getByRole("button", { name: "عرض الخطة الأسبوعية المحدّثة" })
    .click();
  const replacementPlan = await (
    await replacementPlanResponsePromise
  ).json();
  expect(replacementPlan.id).not.toBe(initialPlan.id);
  expect(replacementPlan.assessment_id).toBe(assessmentId);
  expect(replacementPlan.completed_count).toBe(0);
  await expect(page.getByRole("heading", { name: "أصبحت إعادة التقييم متاحة" })).toHaveCount(0);

  await page.reload();
  await expect(page.getByText("الإنجاز — 0 من 14")).toBeVisible();
  await expect(page.getByRole("heading", { name: "أصبحت إعادة التقييم متاحة" })).toHaveCount(0);

  const staleQuestions = await request.get(
    `${apiOrigin}/api/v1/weekly-plans/${initialPlan.id}/followup-questions`,
    { headers: { Authorization: authorization } },
  );
  expect(staleQuestions.status()).toBe(409);
});
