import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as followupsApi from "@/api/followups";
import { queryKeys } from "@/api/queryKeys";

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

export function useCreateFollowup(childId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (assessmentId: string) => followupsApi.createFollowup(assessmentId),
    onSuccess: (followup) => {
      queryClient.setQueryData(queryKeys.followups.detail(followup.id), followup);
      void queryClient.invalidateQueries({ queryKey: queryKeys.followups.forChild(childId) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.weeklyPlan.active(childId) });
    },
  });
}
