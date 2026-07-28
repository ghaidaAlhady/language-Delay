import { apiRequest } from "@/api/client";
import type {
  FollowupResponse,
  WeeklyFollowupContextResponse,
  WeeklyFollowupSubmissionRequest,
} from "@/types/api";

export function getWeeklyFollowupQuestions(
  weeklyPlanId: string,
): Promise<WeeklyFollowupContextResponse> {
  return apiRequest<WeeklyFollowupContextResponse>(
    `/api/v1/weekly-plans/${weeklyPlanId}/followup-questions`,
  );
}

export function submitWeeklyFollowup(
  weeklyPlanId: string,
  payload: WeeklyFollowupSubmissionRequest,
): Promise<FollowupResponse> {
  return apiRequest<FollowupResponse>(`/api/v1/weekly-plans/${weeklyPlanId}/followup`, {
    method: "POST",
    body: payload,
  });
}

export function listFollowups(childId: string): Promise<FollowupResponse[]> {
  return apiRequest<FollowupResponse[]>(`/api/v1/children/${childId}/followups`);
}

export function getFollowup(followupId: string): Promise<FollowupResponse> {
  return apiRequest<FollowupResponse>(`/api/v1/followups/${followupId}`);
}
