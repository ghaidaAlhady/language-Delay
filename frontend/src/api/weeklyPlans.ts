import { apiRequest } from "@/api/client";
import type { WeeklyPlanResponse } from "@/types/api";

export function generateWeeklyPlan(assessmentId: string): Promise<WeeklyPlanResponse> {
  return apiRequest<WeeklyPlanResponse>(`/api/v1/assessments/${assessmentId}/weekly-plan`, {
    method: "POST",
  });
}

export function getActiveWeeklyPlan(childId: string): Promise<WeeklyPlanResponse> {
  return apiRequest<WeeklyPlanResponse>(`/api/v1/children/${childId}/weekly-plan`);
}

export function setActivityCompletion(
  activitySlotId: string,
  completed: boolean,
): Promise<WeeklyPlanResponse> {
  return apiRequest<WeeklyPlanResponse>(`/api/v1/weekly-plan-activities/${activitySlotId}`, {
    method: "PATCH",
    body: { completed },
  });
}

export function requestAlternativeActivity(activitySlotId: string): Promise<WeeklyPlanResponse> {
  return apiRequest<WeeklyPlanResponse>(
    `/api/v1/weekly-plan-activities/${activitySlotId}/alternative`,
    { method: "POST" },
  );
}
