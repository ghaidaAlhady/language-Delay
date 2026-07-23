import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { WeeklyPlanPage } from "@/pages/WeeklyPlanPage";
import { fixtureWeeklyPlan } from "@/tests/fixtures";
import { server } from "@/tests/mocks/server";
import { renderWithProviders, screen, waitFor } from "@/tests/test-utils";

const BASE = import.meta.env.VITE_API_BASE_URL;

describe("WeeklyPlanPage", () => {
  it("groups activities by day and shows the adherence progress", async () => {
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    expect(await screen.findByText("الأحد")).toBeInTheDocument();
    expect(screen.getByText("تنفيذ التعليمات البسيطة")).toBeInTheDocument();
    expect(screen.getByText("لعبة الإشارة")).toBeInTheDocument();
    expect(screen.getByText(/الإنجاز/)).toBeInTheDocument();
  });

  it("shows the no-plan-yet empty state on a 404", async () => {
    server.use(
      http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () =>
        HttpResponse.json({ error: { code: "not_found", message: "no plan" } }, { status: 404 }),
      ),
    );
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    expect(await screen.findByText("لا توجد خطة أسبوعية بعد")).toBeInTheDocument();
  });

  it("marking an activity complete updates the card to the completed state", async () => {
    server.use(
      http.patch(`${BASE}/api/v1/weekly-plan-activities/:slotId`, () =>
        HttpResponse.json({
          ...fixtureWeeklyPlan,
          completed_count: 1,
          activities: fixtureWeeklyPlan.activities.map((a) =>
            a.id === "slot-1" ? { ...a, completed: true, completed_at: "2026-01-01T00:00:00Z" } : a,
          ),
        }),
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    await screen.findByText("تنفيذ التعليمات البسيطة");
    await user.click(screen.getAllByRole("button", { name: "تحديد كمكتمل" })[0]!);

    await waitFor(() => {
      expect(screen.getByText("تم الإنجاز ✓")).toBeInTheDocument();
    });
  });

  it("requesting an alternative activity shows a success toast", async () => {
    server.use(
      http.post(`${BASE}/api/v1/weekly-plan-activities/:slotId/alternative`, () =>
        HttpResponse.json(fixtureWeeklyPlan),
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    await screen.findByText("تنفيذ التعليمات البسيطة");
    await user.click(screen.getAllByRole("button", { name: "طلب نشاط بديل" })[0]!);

    expect(await screen.findByText("تم استبدال النشاط بنشاط بديل.")).toBeInTheDocument();
  });
});
