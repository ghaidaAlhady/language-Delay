import { useQuery } from "@tanstack/react-query";

import * as aiApi from "@/api/aiAssistance";
import { queryKeys } from "@/api/queryKeys";

export function useAssessmentAssistance(assessmentId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.aiAssistance.assessment(assessmentId ?? ""),
    queryFn: () => aiApi.getAssessmentExplanation(assessmentId as string),
    enabled: enabled && Boolean(assessmentId),
    retry: false,
  });
}

export function useWeeklyPlanAssistance(weeklyPlanId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.aiAssistance.weeklyPlan(weeklyPlanId ?? ""),
    queryFn: () => aiApi.getWeeklyPlanSummary(weeklyPlanId as string),
    enabled: enabled && Boolean(weeklyPlanId),
    retry: false,
  });
}

export function useFollowupAssistance(followupId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.aiAssistance.followup(followupId ?? ""),
    queryFn: () => aiApi.getFollowupSummary(followupId as string),
    enabled: enabled && Boolean(followupId),
    retry: false,
  });
}
