import { apiRequest } from "@/api/client";
import type { FollowupResponse } from "@/types/api";

export function createFollowup(assessmentId: string): Promise<FollowupResponse> {
  return apiRequest<FollowupResponse>(`/api/v1/assessments/${assessmentId}/followup`, {
    method: "POST",
  });
}

export function listFollowups(childId: string): Promise<FollowupResponse[]> {
  return apiRequest<FollowupResponse[]>(`/api/v1/children/${childId}/followups`);
}

export function getFollowup(followupId: string): Promise<FollowupResponse> {
  return apiRequest<FollowupResponse>(`/api/v1/followups/${followupId}`);
}
