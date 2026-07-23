import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as childrenApi from "@/api/children";
import { queryKeys } from "@/api/queryKeys";
import type { ChildCreateRequest, ChildUpdateRequest } from "@/types/api";

export function useChildrenList() {
  return useQuery({
    queryKey: queryKeys.children.all,
    queryFn: childrenApi.listChildren,
  });
}

export function useChild(childId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.children.detail(childId ?? ""),
    queryFn: () => childrenApi.getChild(childId as string),
    enabled: Boolean(childId),
  });
}

export function useCreateChild() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ChildCreateRequest) => childrenApi.createChild(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.children.all });
    },
  });
}

export function useUpdateChild(childId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ChildUpdateRequest) => childrenApi.updateChild(childId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.children.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.children.detail(childId) });
    },
  });
}

export function useDeleteChild() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (childId: string) => childrenApi.deleteChild(childId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.children.all });
    },
  });
}
