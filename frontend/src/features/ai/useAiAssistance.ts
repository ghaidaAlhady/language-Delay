import { useQuery } from "@tanstack/react-query";

import * as aiApi from "@/api/aiAssistance";
import { queryKeys } from "@/api/queryKeys";

export function useAssessmentAssistance(assessmentId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.aiAssistance.assessment(assessmentId ?? ""),
    queryFn: () => aiApi.getAssessmentExplanation(assessmentId as string),
    enabled: enabled && Boolean(assessmentId),
    retry: false,
    staleTime: Infinity,
    gcTime: 30 * 60 * 1000,
    refetchOnMount: false,
    refetchOnReconnect: false,
  });
}

export function useWeeklyPlanAssistance(weeklyPlanId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.aiAssistance.weeklyPlan(weeklyPlanId ?? ""),
    queryFn: () => aiApi.getWeeklyPlanSummary(weeklyPlanId as string),
    enabled: enabled && Boolean(weeklyPlanId),
    retry: false,
    staleTime: Infinity,
    gcTime: 30 * 60 * 1000,
    refetchOnMount: false,
    refetchOnReconnect: false,
  });
}

export function useFollowupAssistance(followupId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.aiAssistance.followup(followupId ?? ""),
    queryFn: () => aiApi.getFollowupSummary(followupId as string),
    enabled: enabled && Boolean(followupId),
    retry: false,
    staleTime: Infinity,
    gcTime: 30 * 60 * 1000,
    refetchOnMount: false,
    refetchOnReconnect: false,
  });
}

/** `enabled` is caller-controlled (only fetch once "افهم أكثر" is clicked). */
export function useActivityExplanation(activitySlotId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.aiAssistance.activity(activitySlotId ?? ""),
    queryFn: () => aiApi.getActivityExplanation(activitySlotId as string),
    enabled: enabled && Boolean(activitySlotId),
    retry: false,
    staleTime: Infinity,
    gcTime: 30 * 60 * 1000,
    refetchOnMount: false,
    refetchOnReconnect: false,
  });
}
