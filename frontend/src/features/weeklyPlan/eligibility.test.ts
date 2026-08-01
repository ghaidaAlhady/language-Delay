import { describe, expect, it } from "vitest";

import { activitiesRemainingForEligibility, isReassessmentEligible } from "@/features/weeklyPlan/eligibility";

describe("isReassessmentEligible", () => {
  it.each([
    [7, 10, true],
    [9, 14, false],
    [10, 14, true],
    [14, 14, true],
    [0, 0, false],
    [0, 10, false],
  ])("completed=%i total=%i -> %s", (completed, total, expected) => {
    expect(isReassessmentEligible(completed, total)).toBe(expected);
  });
});

describe("activitiesRemainingForEligibility", () => {
  it.each([
    [7, 10, 0],
    [9, 14, 1],
    [10, 14, 0],
    [14, 14, 0],
    [0, 0, 0],
    [0, 10, 7],
  ])("completed=%i total=%i -> remaining %i", (completed, total, expected) => {
    expect(activitiesRemainingForEligibility(completed, total)).toBe(expected);
  });
});
