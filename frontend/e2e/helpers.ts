import { expect, type Page } from "@playwright/test";

/**
 * One parent account, registered once by global-setup.ts, reused by every
 * spec that just needs "a logged-in parent". Each test still calls
 * `loginExistingParent` itself (never `registerNewParent`) rather than
 * reusing a saved token: the backend *rotates* refresh tokens on every use
 * (a real security feature — old token revoked, new one issued), so a
 * single saved token can only ever be consumed successfully by the first
 * test that uses it. A fresh login, by contrast, always issues its own
 * independent, valid token pair, and `POST /auth/login` has a much more
 * generous rate limit (10/minute) than `/auth/register` (5/minute).
 */
export const SHARED_PARENT_EMAIL = "e2e-shared-parent@example.com";

export function uniqueEmail(tag: string): string {
  return `e2e-${tag}-${Date.now()}-${Math.floor(Math.random() * 100000)}@example.com`;
}

export async function registerNewParent(
  page: Page,
  { email, displayName = "ولي أمر" }: { email: string; displayName?: string },
): Promise<void> {
  await page.goto("/register");
  await page.getByLabel("الاسم").fill(displayName);
  await page.getByLabel("البريد الإلكتروني").fill(email);
  await page.getByLabel("كلمة المرور", { exact: true }).fill("supersecret1");
  await page.getByLabel("تأكيد كلمة المرور").fill("supersecret1");
  await page.getByRole("button", { name: "إنشاء حساب" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

export async function loginExistingParent(page: Page, email: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("البريد الإلكتروني").fill(email);
  await page.getByLabel("كلمة المرور").fill("supersecret1");
  await page.getByRole("button", { name: "تسجيل الدخول" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

export async function addChild(
  page: Page,
  { name, dateOfBirth, gender = "female" }: { name: string; dateOfBirth: string; gender?: "male" | "female" },
): Promise<string> {
  await page.goto("/children/new");
  await page.getByLabel("اسم الطفل").fill(name);
  await page.getByLabel("تاريخ الميلاد").fill(dateOfBirth);
  await page.getByLabel("الجنس").selectOption(gender);
  await page.getByLabel("لغة المنزل").fill("ar");
  await page.getByRole("button", { name: "حفظ" }).click();

  // `/children/new` (the form itself, before submission) matches
  // `/\/children\/[^/]+$/` just as validly as `/children/{realId}` does, so
  // waiting on that URL pattern alone can resolve *before* the real
  // post-creation navigation happens — `page.url()` then reads back the
  // literal string "new" as the "child ID", which 404s on every subsequent
  // request. Waiting for a heading that only ChildDetailPage renders avoids
  // the ambiguity entirely.
  await expect(page.getByRole("heading", { name: "ملف الطفل", exact: true })).toBeVisible();
  const url = page.url();
  const childId = url.split("/children/")[1]?.split(/[/?]/)[0];
  if (!childId || childId === "new") {
    throw new Error(`addChild: could not extract a real child ID from URL: ${url}`);
  }
  return childId;
}

export type AnswerPattern = "all-always" | "all-never" | "alternating";

/**
 * Waits for the take-flow to settle into a definitive, *interactable*
 * state — another question is showing with its answer buttons enabled, or
 * the result page has loaded — and reports which.
 *
 * Several races were found here (all in this test helper, not the app):
 * checking `page.url()` synchronously right after a click races the
 * in-flight navigation (submitting the last answer triggers an async
 * submit-then-complete-then-navigate chain); waiting for a radiogroup to
 * merely be *visible* isn't enough, because the previous question's
 * radiogroup is still visible-but-disabled for a moment while its own
 * submission is in flight, right before it unmounts; and on the *last*
 * question specifically, the already-answered (checked) option can become
 * briefly enabled again for a single render in the gap between the
 * submit-answer and complete-assessment mutations, right before the page
 * navigates to the result. That last window would satisfy a plain
 * "some radio is enabled" check even though it's the same, stale,
 * already-answered question — not a new one. A genuinely fresh question
 * always starts with every option unchecked, so requiring the enabled
 * radio to also be *unchecked* rules that stale window out natively.
 */
async function waitForTakeStep(page: Page): Promise<"question" | "result"> {
  const resultHeading = page.getByRole("heading", { name: "النتيجة الكلية" });
  const freshOption = page.getByRole("radio", { checked: false }).first();

  const outcome = await Promise.race([
    resultHeading.waitFor({ state: "visible", timeout: 30_000 }).then(() => "result" as const),
    expect(freshOption).toBeEnabled({ timeout: 30_000 }).then(() => "question" as const),
  ]);
  return outcome;
}

/** Answers every remaining question on an already-open `/assessments/:id/take` page. */
export async function answerRemainingQuestions(page: Page, pattern: AnswerPattern): Promise<void> {
  for (let i = 0; i < 30; i++) {
    if ((await waitForTakeStep(page)) === "result") break;
    const label =
      pattern === "all-always" ? "دائمًا" : pattern === "all-never" ? "أبدًا" : i % 2 === 0 ? "دائمًا" : "أبدًا";
    await page.getByRole("radio", { name: label }).click();
    await page.getByRole("button", { name: /التالي|عرض النتائج/ }).click();
  }
  await expect(page).toHaveURL(/\/result$/);
}

/** Starts (or resumes) the assessment for a child and answers every question. */
export async function completeAssessment(page: Page, childId: string, pattern: AnswerPattern): Promise<void> {
  await page.goto(`/children/${childId}/assessment/intro`);
  await page.getByRole("button", { name: /ابدأ التقييم|متابعة التقييم الحالي/ }).click();
  await expect(page).toHaveURL(/\/assessments\/.+\/take/);
  await answerRemainingQuestions(page, pattern);
}
