import type { AnswerSubmissionRequest, ResponseValue } from "@/types/api";

/** Builds the exact bulk-upsert payload the backend expects for one answered question. */
export function buildAnswerPayload(questionId: string, response: ResponseValue): AnswerSubmissionRequest {
  return { answers: [{ question_id: questionId, response }] };
}

/**
 * Resume index for the take-flow. The backend only exposes *how many*
 * questions were answered (`answered_count`), not *which* question IDs —
 * so resuming assumes answers were always submitted in the questions'
 * sorted-ID order (which is exactly what this UI does). Clamped to a valid
 * index even if `answeredCount` is stale/out of range.
 */
export function resumeIndex(answeredCount: number, totalQuestions: number): number {
  if (totalQuestions <= 0) return 0;
  return Math.max(0, Math.min(answeredCount, totalQuestions - 1));
}
