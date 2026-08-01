import { apiRequest } from "@/api/client";
import type { ChildCreateRequest, ChildResponse, ChildUpdateRequest } from "@/types/api";

export function listChildren(): Promise<ChildResponse[]> {
  return apiRequest<ChildResponse[]>("/api/v1/children");
}

export function createChild(payload: ChildCreateRequest): Promise<ChildResponse> {
  return apiRequest<ChildResponse>("/api/v1/children", { method: "POST", body: payload });
}

export function getChild(childId: string): Promise<ChildResponse> {
  return apiRequest<ChildResponse>(`/api/v1/children/${childId}`);
}

export function updateChild(childId: string, payload: ChildUpdateRequest): Promise<ChildResponse> {
  return apiRequest<ChildResponse>(`/api/v1/children/${childId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function deleteChild(childId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/children/${childId}`, { method: "DELETE" });
}
