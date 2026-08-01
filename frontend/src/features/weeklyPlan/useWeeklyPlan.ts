import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as weeklyPlansApi from "@/api/weeklyPlans";
import { queryKeys } from "@/api/queryKeys";

export function useActiveWeeklyPlan(childId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.weeklyPlan.active(childId ?? ""),
    queryFn: () => weeklyPlansApi.getActiveWeeklyPlan(childId as string),
    enabled: Boolean(childId),
    retry: (failureCount, error) => {
      // 404 = "no plan generated yet", a legitimate empty state, not a transient failure.
      if (error instanceof Error && error.name === "ApiError" && "status" in error && error.status === 404) {
        return false;
      }
      return failureCount < 1;
    },
  });
}

export function useGenerateWeeklyPlan(childId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (assessmentId: string) => weeklyPlansApi.generateWeeklyPlan(assessmentId),
    onSuccess: (plan) => {
      queryClient.setQueryData(queryKeys.weeklyPlan.active(childId), plan);
    },
  });
}

export function useSetActivityCompletion(childId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ activitySlotId, completed }: { activitySlotId: string; completed: boolean }) =>
      weeklyPlansApi.setActivityCompletion(activitySlotId, completed),
    onSuccess: (plan) => {
      queryClient.setQueryData(queryKeys.weeklyPlan.active(childId), plan);
    },
  });
}

export function useRequestAlternativeActivity(childId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (activitySlotId: string) => weeklyPlansApi.requestAlternativeActivity(activitySlotId),
    onSuccess: (plan) => {
      queryClient.setQueryData(queryKeys.weeklyPlan.active(childId), plan);
    },
  });
}
