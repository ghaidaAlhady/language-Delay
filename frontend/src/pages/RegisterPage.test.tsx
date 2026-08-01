import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { RegisterPage } from "@/pages/RegisterPage";
import { server } from "@/tests/mocks/server";
import { renderWithProviders, screen, waitFor } from "@/tests/test-utils";

const BASE = import.meta.env.VITE_API_BASE_URL;

describe("RegisterPage", () => {
  it("renders all required fields", () => {
    renderWithProviders(<RegisterPage />, { path: "/register", initialEntry: "/register" });
    expect(screen.getByLabelText("الاسم")).toBeInTheDocument();
    expect(screen.getByLabelText("البريد الإلكتروني")).toBeInTheDocument();
    expect(screen.getByLabelText("كلمة المرور", { exact: true })).toBeInTheDocument();
    expect(screen.getByLabelText("تأكيد كلمة المرور")).toBeInTheDocument();
  });

  it("shows a mismatch error when passwords differ", async () => {
    const user = userEvent.setup();
    renderWithProviders(<RegisterPage />, { path: "/register", initialEntry: "/register" });

    await user.type(screen.getByLabelText("الاسم"), "ولي الأمر");
    await user.type(screen.getByLabelText("البريد الإلكتروني"), "parent@example.com");
    await user.type(screen.getByLabelText("كلمة المرور", { exact: true }), "supersecret1");
    await user.type(screen.getByLabelText("تأكيد كلمة المرور"), "different1");
    await user.click(screen.getByRole("button", { name: "إنشاء حساب" }));

    expect(await screen.findByText("كلمتا المرور غير متطابقتين.")).toBeInTheDocument();
  });

  it("navigates to /dashboard on successful registration", async () => {
    const user = userEvent.setup();
    renderWithProviders(<RegisterPage />, {
      path: "/register",
      initialEntry: "/register",
      additionalRoutes: [{ path: "/dashboard", element: <div>لوحة التحكم</div> }],
    });

    await user.type(screen.getByLabelText("الاسم"), "ولي الأمر");
    await user.type(screen.getByLabelText("البريد الإلكتروني"), "parent@example.com");
    await user.type(screen.getByLabelText("كلمة المرور", { exact: true }), "supersecret1");
    await user.type(screen.getByLabelText("تأكيد كلمة المرور"), "supersecret1");
    await user.click(screen.getByRole("button", { name: "إنشاء حساب" }));

    expect(await screen.findByText("لوحة التحكم")).toBeInTheDocument();
  });

  it("shows the duplicate-email Arabic message on a 409", async () => {
    server.use(
      http.post(`${BASE}/api/v1/auth/register`, () =>
        HttpResponse.json(
          { error: { code: "conflict", message: "An account with this email already exists." } },
          { status: 409 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<RegisterPage />, { path: "/register", initialEntry: "/register" });

    await user.type(screen.getByLabelText("الاسم"), "ولي الأمر");
    await user.type(screen.getByLabelText("البريد الإلكتروني"), "parent@example.com");
    await user.type(screen.getByLabelText("كلمة المرور", { exact: true }), "supersecret1");
    await user.type(screen.getByLabelText("تأكيد كلمة المرور"), "supersecret1");
    await user.click(screen.getByRole("button", { name: "إنشاء حساب" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("هذا البريد الإلكتروني مستخدم بالفعل");
    });
  });
});
