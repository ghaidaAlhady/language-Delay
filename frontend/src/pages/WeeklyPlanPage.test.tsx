import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { act } from "react";
import { describe, expect, it } from "vitest";

import { WeeklyPlanPage } from "@/pages/WeeklyPlanPage";
import { fixtureWeeklyPlan } from "@/tests/fixtures";
import { server } from "@/tests/mocks/server";
import { renderWithProviders, screen, waitFor } from "@/tests/test-utils";
import type { WeeklyPlanResponse } from "@/types/api";

const BASE = import.meta.env.VITE_API_BASE_URL;

const completedPlan: WeeklyPlanResponse = {
  ...fixtureWeeklyPlan,
  completed_count: fixtureWeeklyPlan.total_activities,
  adherence_percent: 100,
  activities: fixtureWeeklyPlan.activities.map((activity) => ({
    ...activity,
    completed: true,
    completed_at: "2026-01-08T00:00:00Z",
  })),
};

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
    expect(screen.getAllByRole("button", { name: "تم" })).toHaveLength(2);
    expect(
      screen.queryByRole("link", { name: "ابدأ المتابعة الأسبوعية" }),
    ).not.toBeInTheDocument();
  });

  it("shows the no-plan-yet empty state on a 404", async () => {
    server.use(
      http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () =>
        HttpResponse.json(
          { error: { code: "not_found", message: "no plan" } },
          { status: 404 },
        ),
      ),
    );
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    expect(await screen.findByText("لا توجد خطة أسبوعية بعد")).toBeInTheDocument();
  });

  it("prevents duplicate completion requests and keeps completion after reload", async () => {
    let currentPlan = fixtureWeeklyPlan;
    let requestCount = 0;
    server.use(
      http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () =>
        HttpResponse.json(currentPlan),
      ),
      http.patch(`${BASE}/api/v1/weekly-plan-activities/:slotId`, async () => {
        requestCount += 1;
        await new Promise((resolve) => setTimeout(resolve, 25));
        currentPlan = {
          ...currentPlan,
          completed_count: 1,
          adherence_percent: 50,
          activities: currentPlan.activities.map((activity) =>
            activity.id === "slot-1"
              ? {
                  ...activity,
                  completed: true,
                  completed_at: "2026-01-01T00:00:00Z",
                }
              : activity,
          ),
        };
        return HttpResponse.json(currentPlan);
      }),
    );
    const firstRender = renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    await screen.findByText("تنفيذ التعليمات البسيطة");
    const completionButton = screen.getAllByRole("button", { name: "تم" })[0]!;
    act(() => {
      completionButton.click();
      completionButton.click();
    });

    await waitFor(() => {
      expect(screen.getByText("مكتمل ✓")).toBeInTheDocument();
      expect(requestCount).toBe(1);
    });

    firstRender.unmount();
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });
    expect(
      (await screen.findAllByRole("button", { name: "مكتمل" })).length,
    ).toBeGreaterThan(0);
  });

  it("shows the exact follow-up panel only for the fully completed active plan", async () => {
    server.use(
      http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () =>
        HttpResponse.json(completedPlan),
      ),
    );
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    expect(await screen.findByText("أكملتم الخطة الأسبوعية")).toBeInTheDocument();
    expect(
      screen.getByText("حان وقت تقييم تقدم الطفل وإنشاء خطة الأسبوع القادم."),
    ).toBeInTheDocument();
    const link = screen.getByRole("link", {
      name: "ابدأ المتابعة الأسبوعية",
    });
    expect(link).toHaveAttribute(
      "href",
      "/children/child-1/reassessment?planId=plan-1",
    );
  });

  it("does not prompt from an inactive completed plan", async () => {
    server.use(
      http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () =>
        HttpResponse.json({ ...completedPlan, is_active: false }),
      ),
    );
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    await screen.findByText("تنفيذ التعليمات البسيطة");
    expect(screen.queryByText("أكملتم الخطة الأسبوعية")).not.toBeInTheDocument();
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
    await user.click(
      screen.getAllByRole("button", { name: "طلب نشاط بديل" })[0]!,
    );

    expect(
      await screen.findByText("تم استبدال النشاط بنشاط بديل."),
    ).toBeInTheDocument();
  });

  it("adds the optional summary without replacing plan activities", async () => {
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    expect(
      await screen.findByRole("heading", { name: "ملخص الخطة الأسبوعية" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("صياغة مساندة بالذكاء الاصطناعي"),
    ).toBeInTheDocument();
    expect(screen.getByText("تنفيذ التعليمات البسيطة")).toBeInTheDocument();
  });
});
