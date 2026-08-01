/**
 * Mirrors the backend's integer-safe 70% reassessment-eligibility rule
 * exactly (`backend/app/services/weekly_plan_service.py`). The backend
 * remains authoritative — this is a display-only mirror so the UI can show
 * the right state without an extra round trip; the API itself still
 * enforces the threshold independently.
 */
const REASSESSMENT_ELIGIBILITY_PERCENT = 70;

export function isReassessmentEligible(completedCount: number, totalActivities: number): boolean {
  if (totalActivities === 0) return false;
  return completedCount * 100 >= totalActivities * REASSESSMENT_ELIGIBILITY_PERCENT;
}

export function activitiesRemainingForEligibility(
  completedCount: number,
  totalActivities: number,
): number {
  if (totalActivities === 0) return 0;
  const needed = Math.ceil((totalActivities * REASSESSMENT_ELIGIBILITY_PERCENT) / 100);
  return Math.max(0, needed - completedCount);
}
