import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { ToastProvider } from "@/components/ToastProvider";
import { AuthProvider } from "@/features/auth/AuthProvider";
import { clearTokens, setRefreshToken } from "@/services/tokenStore";

interface RenderOptions {
  /** Seeds a refresh token so AuthProvider's bootstrap resolves to "authenticated" via MSW. */
  authenticated?: boolean;
  /** The router path pattern the element is mounted at (supports :params). */
  path?: string;
  /** The URL to start the in-memory router at. */
  initialEntry?: string;
  /** Extra routes (e.g. a redirect target) mounted alongside the main one. */
  additionalRoutes?: { path: string; element: ReactElement }[];
}

export function renderWithProviders(
  ui: ReactElement,
  {
    authenticated = false,
    path = "/",
    initialEntry = "/",
    additionalRoutes = [],
  }: RenderOptions = {},
): RenderResult {
  if (authenticated) {
    setRefreshToken("seeded-refresh-token");
  } else {
    clearTokens();
  }

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <AuthProvider>
            <Routes>
              <Route path={path} element={ui} />
              {additionalRoutes.map((route) => (
                <Route key={route.path} path={route.path} element={route.element} />
              ))}
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

export * from "@testing-library/react";
