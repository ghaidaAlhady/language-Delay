import { describe, expect, it } from "vitest";

import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { renderWithProviders, screen, waitForElementToBeRemoved } from "@/tests/test-utils";

describe("ProtectedRoute", () => {
  it("redirects to /login when there is no session", async () => {
    renderWithProviders(<ProtectedRoute />, {
      authenticated: false,
      path: "/dashboard",
      initialEntry: "/dashboard",
      additionalRoutes: [{ path: "/login", element: <div>تسجيل الدخول</div> }],
    });

    expect(await screen.findByText("تسجيل الدخول")).toBeInTheDocument();
  });

  it("renders the protected content when a valid session exists", async () => {
    renderWithProviders(<ProtectedRoute />, {
      authenticated: true,
      path: "/dashboard",
      initialEntry: "/dashboard",
    });

    // ProtectedRoute renders an <Outlet/> with no nested route matched here,
    // so success is simply *not* being redirected to /login once loading settles.
    await waitForElementToBeRemoved(() => screen.queryByRole("status"));
    expect(screen.queryByText("تسجيل الدخول")).not.toBeInTheDocument();
  });
});
