import { apiRequest } from "@/api/client";
import type { AIAssistanceResponse } from "@/types/api";

export function getAssessmentExplanation(assessmentId: string): Promise<AIAssistanceResponse> {
  return apiRequest(`/api/v1/assessments/${assessmentId}/ai-explanation`, {
    method: "POST",
  });
}

export function getWeeklyPlanSummary(weeklyPlanId: string): Promise<AIAssistanceResponse> {
  return apiRequest(`/api/v1/weekly-plans/${weeklyPlanId}/ai-summary`, {
    method: "POST",
  });
}

export function getFollowupSummary(followupId: string): Promise<AIAssistanceResponse> {
  return apiRequest(`/api/v1/followups/${followupId}/ai-summary`, {
    method: "POST",
  });
}
