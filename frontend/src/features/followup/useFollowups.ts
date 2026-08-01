import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as followupsApi from "@/api/followups";
import { queryKeys } from "@/api/queryKeys";
import type { WeeklyFollowupSubmissionRequest } from "@/types/api";

export function useFollowupsForChild(childId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.followups.forChild(childId ?? ""),
    queryFn: () => followupsApi.listFollowups(childId as string),
    enabled: Boolean(childId),
  });
}

export function useFollowup(followupId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.followups.detail(followupId ?? ""),
    queryFn: () => followupsApi.getFollowup(followupId as string),
    enabled: Boolean(followupId),
  });
}

export function useWeeklyFollowupQuestions(weeklyPlanId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.followups.questions(weeklyPlanId ?? ""),
    queryFn: () => followupsApi.getWeeklyFollowupQuestions(weeklyPlanId as string),
    enabled: Boolean(weeklyPlanId),
  });
}

export function useSubmitWeeklyFollowup(childId: string, weeklyPlanId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: WeeklyFollowupSubmissionRequest) =>
      followupsApi.submitWeeklyFollowup(weeklyPlanId, payload),
    onSuccess: (followup) => {
      queryClient.setQueryData(queryKeys.followups.detail(followup.id), followup);
      void queryClient.invalidateQueries({ queryKey: queryKeys.followups.forChild(childId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.weeklyPlan.active(childId) });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.followups.questions(weeklyPlanId),
      });
    },
  });
}
