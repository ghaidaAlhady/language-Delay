import { describe, expect, it } from "vitest";

import { buildAnswerPayload, resumeIndex } from "@/features/assessment/answerMapping";

describe("buildAnswerPayload", () => {
  it("wraps one question/response pair into the bulk-upsert shape", () => {
    expect(buildAnswerPayload("Q005", "often")).toEqual({
      answers: [{ question_id: "Q005", response: "often" }],
    });
  });
});

describe("resumeIndex", () => {
  it("resumes at answeredCount when within range", () => {
    expect(resumeIndex(3, 20)).toBe(3);
  });

  it("clamps to the last question when answeredCount equals the total", () => {
    expect(resumeIndex(20, 20)).toBe(19);
  });

  it("clamps to the last question when answeredCount exceeds the total", () => {
    expect(resumeIndex(99, 20)).toBe(19);
  });

  it("never returns a negative index", () => {
    expect(resumeIndex(-1, 20)).toBe(0);
  });

  it("returns 0 when there are no questions", () => {
    expect(resumeIndex(0, 0)).toBe(0);
  });
});
