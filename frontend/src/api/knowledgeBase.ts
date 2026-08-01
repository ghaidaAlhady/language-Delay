import { apiRequest } from "@/api/client";
import type { ActivityRecord, Domain, ReferenceRecord } from "@/types/api";

export function listActivities(age: number, domain?: Domain): Promise<ActivityRecord[]> {
  return apiRequest<ActivityRecord[]>("/api/v1/activities", { query: { age, domain } });
}

export function getAssessmentActivities(assessmentId: string): Promise<ActivityRecord[]> {
  return apiRequest<ActivityRecord[]>(`/api/v1/assessments/${assessmentId}/activities`);
}

export function listReferences(): Promise<ReferenceRecord[]> {
  return apiRequest<ReferenceRecord[]>("/api/v1/references");
}
