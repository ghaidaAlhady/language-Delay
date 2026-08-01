import { QueryClient, QueryClientProvider, onlineManager } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NetworkError } from "@/api/ApiError";
import * as childrenApi from "@/api/children";
import { useCreateChild } from "@/features/children/useChildren";
import type { ChildCreateRequest } from "@/types/api";

const childPayload: ChildCreateRequest = {
  name: "Offline child",
  date_of_birth: "2022-01-15",
  gender: "female",
  home_language: "ar",
  has_previous_diagnosis: false,
  previous_diagnosis_details: null,
  has_hearing_problems: false,
  uses_hearing_aid: false,
  notes: null,
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("useCreateChild", () => {
  afterEach(() => {
    onlineManager.setOnline(true);
    vi.restoreAllMocks();
  });

  it("runs the mutation while offline so the page can show the offline error", async () => {
    const createChild = vi.spyOn(childrenApi, "createChild").mockRejectedValue(new NetworkError());
    onlineManager.setOnline(false);

    const { result } = renderHook(() => useCreateChild(), { wrapper: createWrapper() });

    act(() => {
      result.current.mutate(childPayload);
    });

    await waitFor(() => expect(createChild).toHaveBeenCalledOnce());
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
