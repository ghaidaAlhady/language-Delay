import { expect, test } from "@playwright/test";

import { addChild, completeAssessment, loginExistingParent, SHARED_PARENT_EMAIL } from "./helpers";

test("Case 3: mixed-answer assessment completes and shows per-domain variation", async ({ page }) => {
  await loginExistingParent(page, SHARED_PARENT_EMAIL);
  const childId = await addChild(page, { name: "طفل تقييم مختلط", dateOfBirth: "2022-01-15" });

  await completeAssessment(page, childId, "alternating");

  await expect(page.getByText("النتيجة الكلية")).toBeVisible();
  const domainScores = await page.locator("text=/النسبة: [٠-٩]+%/").allTextContents();
  expect(domainScores.length).toBeGreaterThan(0);
  // A mixed always/never pattern must not produce the trivial all-100 outcome.
  expect(domainScores.every((score) => score === "النسبة: ١٠٠%")).toBe(false);
});
