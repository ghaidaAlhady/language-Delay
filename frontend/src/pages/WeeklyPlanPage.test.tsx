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

  it("enables reassessment for a fully completed (100%) active plan", async () => {
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

    expect(await screen.findByText("أصبحت إعادة التقييم متاحة")).toBeInTheDocument();
    expect(
      screen.getByText("أكملتِ 2 من 2 نشاطًا — أصبحت إعادة التقييم متاحة."),
    ).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "بدء إعادة التقييم" });
    expect(link).toHaveAttribute(
      "href",
      "/children/child-1/reassessment?planId=plan-1",
    );
  });

  it("shows a disabled button and the 70% message below the eligibility threshold", async () => {
    // 1/2 completed: below 70%, and exactly 1 more activity is needed.
    const almostPlan: WeeklyPlanResponse = {
      ...fixtureWeeklyPlan,
      completed_count: 1,
      activities: fixtureWeeklyPlan.activities.map((activity, index) => ({
        ...activity,
        completed: index === 0,
      })),
    };
    server.use(
      http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () =>
        HttpResponse.json(almostPlan),
      ),
    );
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    await screen.findByText("تنفيذ التعليمات البسيطة");
    expect(
      screen.getByText("يمكنك بدء إعادة التقييم بعد إكمال 70% من الأنشطة."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("أكملي نشاطًا واحدًا إضافيًا لفتح إعادة التقييم."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "إعادة التقييم الأسبوعي" })).toBeDisabled();
  });

  it("enables reassessment exactly at the 70% threshold", async () => {
    const eligiblePlan: WeeklyPlanResponse = {
      ...fixtureWeeklyPlan,
      total_activities: 10,
      completed_count: 7,
      activities: Array.from({ length: 10 }, (_, index) => ({
        ...fixtureWeeklyPlan.activities[0]!,
        id: `slot-${index}`,
        slot_order: index + 1,
        completed: index < 7,
      })),
    };
    server.use(
      http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () =>
        HttpResponse.json(eligiblePlan),
      ),
    );
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    expect(await screen.findByText("أصبحت إعادة التقييم متاحة")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "بدء إعادة التقييم" })).toBeInTheDocument();
  });

  it("shows a resume label when the backend reports a frozen reassessment", async () => {
    server.use(
      http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () =>
        HttpResponse.json({ ...completedPlan, reassessment_started: true }),
      ),
    );
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    expect(await screen.findByRole("link", { name: "متابعة إعادة التقييم" })).toBeInTheDocument();
  });

  it("disables activity replacement after reassessment questions are frozen", async () => {
    server.use(
      http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () =>
        HttpResponse.json({ ...fixtureWeeklyPlan, reassessment_started: true }),
      ),
    );
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    await screen.findByText("تنفيذ التعليمات البسيطة");
    for (const button of screen.getAllByRole("button", { name: "طلب نشاط بديل" })) {
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute(
        "title",
        "لا يمكن تغيير الأنشطة بعد بدء إعادة التقييم",
      );
    }
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
    expect(screen.queryByText("أصبحت إعادة التقييم متاحة")).not.toBeInTheDocument();
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

  it("deduplicates rapid alternative-activity clicks for the same slot", async () => {
    let requestCount = 0;
    server.use(
      http.post(`${BASE}/api/v1/weekly-plan-activities/:slotId/alternative`, async () => {
        requestCount += 1;
        await new Promise((resolve) => setTimeout(resolve, 25));
        return HttpResponse.json(fixtureWeeklyPlan);
      }),
    );
    const user = userEvent.setup();
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    await screen.findByText("تنفيذ التعليمات البسيطة");
    await user.dblClick(
      screen.getAllByRole("button", { name: "طلب نشاط بديل" })[0]!,
    );

    await screen.findByText("تم استبدال النشاط بنشاط بديل.");
    expect(requestCount).toBe(1);
  });

  it("افهم أكثر: fetches once per activity and prevents duplicate requests while pending", async () => {
    let requestCount = 0;
    server.use(
      http.post(`${BASE}/api/v1/weekly-plan-activities/:slotId/ai-explanation`, async () => {
        requestCount += 1;
        await new Promise((resolve) => setTimeout(resolve, 25));
        return HttpResponse.json({
          content: {
            activity_id: "A001",
            title_ar: "أكمل الجملة",
            simple_explanation_ar: "شرح مبسط.",
            purpose_ar: "الهدف.",
            steps_ar: ["خطوة أولى", "خطوة ثانية", "خطوة ثالثة"],
            example_dialogue: {
              parent_text: "هيا نجرّب.",
              example_child_response: "مثال محتمل.",
              supportive_parent_continuation: "أحسنت.",
            },
            alternative_ar: "طريقة أسهل.",
            source_ids: ["A001"],
          },
          generation_source: "gemini",
          fallback_reason: null,
          prompt_version: "v2",
          source_references: [{ source_id: "A001", label_ar: "أكمل الجملة", category: "نشاط معتمد" }],
        });
      }),
    );
    const user = userEvent.setup();
    renderWithProviders(<WeeklyPlanPage />, {
      authenticated: true,
      path: "/children/:childId/weekly-plan",
      initialEntry: "/children/child-1/weekly-plan",
    });

    await screen.findByText("تنفيذ التعليمات البسيطة");
    const explainButtons = screen.getAllByRole("button", { name: "افهم أكثر" });
    await user.dblClick(explainButtons[0]!);

    expect(await screen.findByText("شرح مبسط.")).toBeInTheDocument();
    expect(requestCount).toBe(1);
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
