import { QueryClient } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { useAuth } from "@/features/auth/useAuth";
import { renderWithProviders, screen, waitFor } from "@/tests/test-utils";

function AuthCacheHarness() {
  const { status, login, logout } = useAuth();

  return (
    <div>
      <p data-testid="auth-status">{status}</p>
      <button type="button" onClick={() => void login("parent@example.com", "supersecret1")}>
        دخول
      </button>
      <button type="button" onClick={() => void logout()}>
        خروج
      </button>
    </div>
  );
}

function createSeededQueryClient(): QueryClient {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  queryClient.setQueryData(["children"], [{ id: "child-from-previous-account" }]);
  queryClient.setQueryData(["weeklyPlan", "old-child"], { id: "old-plan" });
  return queryClient;
}

describe("AuthProvider account cache isolation", () => {
  it("clears private cached data before activating a newly logged-in account", async () => {
    const user = userEvent.setup();
    const queryClient = createSeededQueryClient();

    renderWithProviders(<AuthCacheHarness />, { queryClient });

    await waitFor(() => {
      expect(screen.getByTestId("auth-status")).toHaveTextContent("unauthenticated");
    });

    await user.click(screen.getByRole("button", { name: "دخول" }));

    await waitFor(() => {
      expect(screen.getByTestId("auth-status")).toHaveTextContent("authenticated");
    });

    expect(queryClient.getQueryData(["children"])).toBeUndefined();
    expect(queryClient.getQueryData(["weeklyPlan", "old-child"])).toBeUndefined();
    expect(queryClient.getMutationCache().getAll()).toHaveLength(0);
  });

  it("clears private cached data when the authenticated account logs out", async () => {
    const user = userEvent.setup();
    const queryClient = createSeededQueryClient();

    renderWithProviders(<AuthCacheHarness />, { authenticated: true, queryClient });

    await waitFor(() => {
      expect(screen.getByTestId("auth-status")).toHaveTextContent("authenticated");
    });

    await user.click(screen.getByRole("button", { name: "خروج" }));

    await waitFor(() => {
      expect(screen.getByTestId("auth-status")).toHaveTextContent("unauthenticated");
    });

    expect(queryClient.getQueryData(["children"])).toBeUndefined();
    expect(queryClient.getQueryData(["weeklyPlan", "old-child"])).toBeUndefined();
    expect(queryClient.getMutationCache().getAll()).toHaveLength(0);
  });
});
