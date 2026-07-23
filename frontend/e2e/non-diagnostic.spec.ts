import { expect, test } from "@playwright/test";

import { addChild, completeAssessment, loginExistingParent, SHARED_PARENT_EMAIL } from "./helpers";

/**
 * The word "تشخيص" (diagnosis) may only ever appear as part of an explicit
 * *denial* that the app diagnoses anything (e.g. "لا يمثل تشخيصًا طبيًا" —
 * "does not represent a medical diagnosis"). It must never appear as a
 * standalone claim. This walks the core result/report pages and asserts
 * every occurrence is immediately preceded by a negation word.
 */
function assertNoUnnegatedDiagnosisClaim(bodyText: string): void {
  const occurrences = [...bodyText.matchAll(/تشخيص/g)];
  for (const match of occurrences) {
    const start = match.index ?? 0;
    const before = bodyText.slice(Math.max(0, start - 12), start);
    expect(before, `"تشخيص" appeared without a preceding negation: "...${before}تشخيص..."`).toMatch(
      /لا |ليس /,
    );
  }
}

test("no diagnostic medical claim appears on the assessment result page", async ({ page }) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  const childId = await addChild(page, { name: "طفل فحص الصياغة", dateOfBirth: "2022-01-15" });
  await completeAssessment(page, childId, "all-never");

  const bodyText = await page.locator("body").innerText();
  assertNoUnnegatedDiagnosisClaim(bodyText);
});

test("no diagnostic medical claim appears on the generated report page", async ({ page }) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  const childId = await addChild(page, { name: "طفل فحص التقرير", dateOfBirth: "2022-01-15" });
  await completeAssessment(page, childId, "all-never");

  await page.getByRole("button", { name: "عرض التقرير" }).click();
  await expect(page).toHaveURL(/\/reports\/.+/);

  // The report must carry the non-diagnostic disclaimer somewhere on the page.
  await expect(page.getByText(/لا يغني عن التقييم أو العلاج من قبل أخصائي تخاطب مؤهل/)).toBeVisible();

  const bodyText = await page.locator("body").innerText();
  assertNoUnnegatedDiagnosisClaim(bodyText);
});
