import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { ChildDetailPage } from "@/pages/ChildDetailPage";
import { server } from "@/tests/mocks/server";
import { renderWithProviders, screen } from "@/tests/test-utils";

const BASE = import.meta.env.VITE_API_BASE_URL;

describe("ChildDetailPage", () => {
  it("shows the delete confirmation dialog and does not delete until confirmed", async () => {
    let deleteCalled = false;
    server.use(
      http.delete(`${BASE}/api/v1/children/:childId`, () => {
        deleteCalled = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );

    const user = userEvent.setup();
    renderWithProviders(<ChildDetailPage />, {
      authenticated: true,
      path: "/children/:childId",
      initialEntry: "/children/child-1",
    });

    await screen.findByText("ملف الطفل");
    await user.click(screen.getByRole("button", { name: "حذف" }));

    expect(screen.getByText(/سيتم حذف جميع التقييمات والتقارير والخطط/)).toBeInTheDocument();
    expect(deleteCalled).toBe(false);

    await user.click(screen.getByRole("button", { name: "إلغاء" }));
    expect(deleteCalled).toBe(false);
  });

  it("deletes the child after confirming", async () => {
    let deleteCalled = false;
    server.use(
      http.delete(`${BASE}/api/v1/children/:childId`, () => {
        deleteCalled = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );

    const user = userEvent.setup();
    renderWithProviders(<ChildDetailPage />, {
      authenticated: true,
      path: "/children/:childId",
      initialEntry: "/children/child-1",
      additionalRoutes: [{ path: "/children", element: <div>أطفالي</div> }],
    });

    await screen.findByText("ملف الطفل");
    await user.click(screen.getByRole("button", { name: "حذف" }));
    await user.click(screen.getByRole("button", { name: "حذف نهائي" }));

    expect(await screen.findByText("أطفالي")).toBeInTheDocument();
    expect(deleteCalled).toBe(true);
  });

  it("shows an age-ineligibility notice and hides the start-assessment action when out of range", async () => {
    server.use(
      http.get(`${BASE}/api/v1/children/:childId`, () =>
        HttpResponse.json({
          id: "child-1",
          name: "سارة",
          date_of_birth: "2015-01-01",
          gender: "female",
          home_language: "ar",
          has_previous_diagnosis: false,
          previous_diagnosis_details: null,
          has_hearing_problems: false,
          uses_hearing_aid: false,
          notes: null,
          age_years: 10,
          is_assessment_age_eligible: false,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        }),
      ),
    );

    renderWithProviders(<ChildDetailPage />, {
      authenticated: true,
      path: "/children/:childId",
      initialEntry: "/children/child-1",
    });

    expect(await screen.findByText(/خارج النطاق المدعوم للتقييم/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "بدء تقييم" })).not.toBeInTheDocument();
  });
});
