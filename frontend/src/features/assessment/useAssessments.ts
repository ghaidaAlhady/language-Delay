import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as assessmentsApi from "@/api/assessments";
import { queryKeys } from "@/api/queryKeys";
import type { AnswerSubmissionRequest } from "@/types/api";

export function useAssessmentsForChild(childId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.assessments.forChild(childId ?? ""),
    queryFn: () => assessmentsApi.listAssessments(childId as string),
    enabled: Boolean(childId),
  });
}

export function useAssessment(assessmentId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.assessments.detail(assessmentId ?? ""),
    queryFn: () => assessmentsApi.getAssessment(assessmentId as string),
    enabled: Boolean(assessmentId),
  });
}

export function useAssessmentQuestions(assessmentId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.assessments.questions(assessmentId ?? ""),
    queryFn: () => assessmentsApi.getAssessmentQuestions(assessmentId as string),
    enabled: Boolean(assessmentId),
  });
}

export function useStartAssessment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (childId: string) => assessmentsApi.startAssessment(childId),
    onSuccess: (assessment) => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.assessments.forChild(assessment.child_id),
      });
    },
  });
}

export function useSubmitAnswers(assessmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AnswerSubmissionRequest) =>
      assessmentsApi.submitAnswers(assessmentId, payload),
    onSuccess: (assessment) => {
      queryClient.setQueryData(queryKeys.assessments.detail(assessmentId), assessment);
    },
  });
}

export function useCompleteAssessment(assessmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => assessmentsApi.completeAssessment(assessmentId),
    onSuccess: (assessment) => {
      queryClient.setQueryData(queryKeys.assessments.detail(assessmentId), assessment);
      void queryClient.invalidateQueries({
        queryKey: queryKeys.assessments.forChild(assessment.child_id),
      });
    },
  });
}
