import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { BackendAvailabilityGate } from "@/app/BackendAvailabilityGate";
import { ToastProvider } from "@/components/ToastProvider";
import { AuthProvider } from "@/features/auth/AuthProvider";

function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        staleTime: 30_000,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}

const queryClient = createQueryClient();

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BackendAvailabilityGate>
          <AuthProvider>{children}</AuthProvider>
        </BackendAvailabilityGate>
      </ToastProvider>
    </QueryClientProvider>
  );
}
