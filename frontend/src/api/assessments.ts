import { apiRequest } from "@/api/client";
import type {
  AnswerSubmissionRequest,
  AssessmentQuestionResponse,
  AssessmentResponse,
} from "@/types/api";

export function getQuestionsByAge(age: number): Promise<AssessmentQuestionResponse[]> {
  return apiRequest<AssessmentQuestionResponse[]>("/api/v1/assessment-questions", {
    query: { age },
  });
}

export function startAssessment(childId: string): Promise<AssessmentResponse> {
  return apiRequest<AssessmentResponse>(`/api/v1/children/${childId}/assessments`, {
    method: "POST",
  });
}

export function listAssessments(childId: string): Promise<AssessmentResponse[]> {
  return apiRequest<AssessmentResponse[]>(`/api/v1/children/${childId}/assessments`);
}

export function getAssessment(assessmentId: string): Promise<AssessmentResponse> {
  return apiRequest<AssessmentResponse>(`/api/v1/assessments/${assessmentId}`);
}

export function getAssessmentQuestions(assessmentId: string): Promise<AssessmentQuestionResponse[]> {
  return apiRequest<AssessmentQuestionResponse[]>(`/api/v1/assessments/${assessmentId}/questions`);
}

export function submitAnswers(
  assessmentId: string,
  payload: AnswerSubmissionRequest,
): Promise<AssessmentResponse> {
  return apiRequest<AssessmentResponse>(`/api/v1/assessments/${assessmentId}/answers`, {
    method: "POST",
    body: payload,
  });
}

export function completeAssessment(assessmentId: string): Promise<AssessmentResponse> {
  return apiRequest<AssessmentResponse>(`/api/v1/assessments/${assessmentId}/complete`, {
    method: "POST",
  });
}
