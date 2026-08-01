import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { LoginPage } from "@/pages/LoginPage";
import { server } from "@/tests/mocks/server";
import { renderWithProviders, screen, waitFor } from "@/tests/test-utils";

const BASE = import.meta.env.VITE_API_BASE_URL;

describe("LoginPage", () => {
  it("renders labeled email and password fields and a submit button", () => {
    renderWithProviders(<LoginPage />, { path: "/login", initialEntry: "/login" });
    expect(screen.getByLabelText("البريد الإلكتروني")).toBeInTheDocument();
    expect(screen.getByLabelText("كلمة المرور")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "تسجيل الدخول" })).toBeInTheDocument();
  });

  it("shows Arabic validation errors when submitted empty", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { path: "/login", initialEntry: "/login" });

    await user.click(screen.getByRole("button", { name: "تسجيل الدخول" }));

    expect(await screen.findByText("البريد الإلكتروني مطلوب.")).toBeInTheDocument();
    expect(await screen.findByText("كلمة المرور مطلوبة.")).toBeInTheDocument();
  });

  it("navigates to /dashboard on successful login", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, {
      path: "/login",
      initialEntry: "/login",
      additionalRoutes: [{ path: "/dashboard", element: <div>لوحة التحكم</div> }],
    });

    await user.type(screen.getByLabelText("البريد الإلكتروني"), "parent@example.com");
    await user.type(screen.getByLabelText("كلمة المرور"), "supersecret1");
    await user.click(screen.getByRole("button", { name: "تسجيل الدخول" }));

    expect(await screen.findByText("لوحة التحكم")).toBeInTheDocument();
  });

  it("shows the wrong-credentials Arabic message on a 401", async () => {
    server.use(
      http.post(`${BASE}/api/v1/auth/login`, () =>
        HttpResponse.json(
          { error: { code: "unauthorized", message: "Invalid email or password." } },
          { status: 401 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { path: "/login", initialEntry: "/login" });

    await user.type(screen.getByLabelText("البريد الإلكتروني"), "parent@example.com");
    await user.type(screen.getByLabelText("كلمة المرور"), "wrong");
    await user.click(screen.getByRole("button", { name: "تسجيل الدخول" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("البريد الإلكتروني أو كلمة المرور غير صحيحة.");
    });
  });
});
