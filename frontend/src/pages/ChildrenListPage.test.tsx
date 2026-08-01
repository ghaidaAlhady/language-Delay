import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { ChildrenListPage } from "@/pages/ChildrenListPage";
import { fixtureChild } from "@/tests/fixtures";
import { server } from "@/tests/mocks/server";
import { renderWithProviders, screen, waitFor } from "@/tests/test-utils";

const BASE = import.meta.env.VITE_API_BASE_URL;

describe("ChildrenListPage", () => {
  it("shows the empty state when the parent has no children", async () => {
    server.use(http.get(`${BASE}/api/v1/children`, () => HttpResponse.json([])));
    renderWithProviders(<ChildrenListPage />, { authenticated: true });

    expect(await screen.findByText("لا يوجد أطفال بعد")).toBeInTheDocument();
  });

  it("renders a card per child on success", async () => {
    server.use(http.get(`${BASE}/api/v1/children`, () => HttpResponse.json([fixtureChild])));
    renderWithProviders(<ChildrenListPage />, { authenticated: true });

    expect(await screen.findByText("سارة")).toBeInTheDocument();
  });

  it("shows an Arabic error state with a retry action on failure", async () => {
    server.use(
      http.get(`${BASE}/api/v1/children`, () =>
        HttpResponse.json({ error: { code: "internal_error", message: "boom" } }, { status: 500 }),
      ),
    );
    renderWithProviders(<ChildrenListPage />, { authenticated: true });

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("حدث خطأ في الخادم");
    });
    expect(screen.getByRole("button", { name: "إعادة المحاولة" })).toBeInTheDocument();
  });
});
