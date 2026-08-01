import { AI_REQUEST_TIMEOUT_MS, apiRequest } from "@/api/client";
import type { ActivityExplanationResponse, AIAssistanceResponse } from "@/types/api";

export function getAssessmentExplanation(assessmentId: string): Promise<AIAssistanceResponse> {
  return apiRequest(`/api/v1/assessments/${assessmentId}/ai-explanation`, {
    method: "POST",
    timeoutMs: AI_REQUEST_TIMEOUT_MS,
  });
}

export function getWeeklyPlanSummary(weeklyPlanId: string): Promise<AIAssistanceResponse> {
  return apiRequest(`/api/v1/weekly-plans/${weeklyPlanId}/ai-summary`, {
    method: "POST",
    timeoutMs: AI_REQUEST_TIMEOUT_MS,
  });
}

export function getFollowupSummary(followupId: string): Promise<AIAssistanceResponse> {
  return apiRequest(`/api/v1/followups/${followupId}/ai-summary`, {
    method: "POST",
    timeoutMs: AI_REQUEST_TIMEOUT_MS,
  });
}

export function getActivityExplanation(
  activitySlotId: string,
): Promise<ActivityExplanationResponse> {
  return apiRequest(`/api/v1/weekly-plan-activities/${activitySlotId}/ai-explanation`, {
    method: "POST",
    timeoutMs: AI_REQUEST_TIMEOUT_MS,
  });
}
