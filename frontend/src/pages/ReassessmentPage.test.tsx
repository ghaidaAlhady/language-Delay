import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { act } from "react";
import { describe, expect, it } from "vitest";

import { ReassessmentPage } from "@/pages/ReassessmentPage";
import {
  fixtureFollowup,
  fixtureWeeklyFollowupContext,
  fixtureWeeklyPlan,
} from "@/tests/fixtures";
import { server } from "@/tests/mocks/server";
import { renderWithProviders, screen, waitFor } from "@/tests/test-utils";

const BASE = import.meta.env.VITE_API_BASE_URL;
const completedPlan = {
  ...fixtureWeeklyPlan,
  completed_count: fixtureWeeklyPlan.total_activities,
  adherence_percent: 100,
  activities: fixtureWeeklyPlan.activities.map((activity) => ({
    ...activity,
    completed: true,
    completed_at: "2026-01-08T00:00:00Z",
  })),
};

describe("ReassessmentPage", () => {
  it("shows child/plan context and 5-8 KB06 questions without auto-submitting", async () => {
    let submissionCount = 0;
    server.use(
      http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () =>
        HttpResponse.json(completedPlan),
      ),
      http.post(`${BASE}/api/v1/weekly-plans/:planId/followup`, () => {
        submissionCount += 1;
        return HttpResponse.json(fixtureFollowup, { status: 201 });
      }),
    );

    renderWithProviders(<ReassessmentPage />, {
      authenticated: true,
      path: "/children/:childId/reassessment",
      initialEntry: "/children/child-1/reassessment?planId=plan-1",
    });

    expect(
      await screen.findByRole("heading", { name: "المتابعة الأسبوعية" }),
    ).toBeInTheDocument();
    expect(screen.getByText("الطفل: سارة")).toBeInTheDocument();
    expect(screen.getByText(/الخطة النشطة منذ/)).toBeInTheDocument();
    expect(screen.getByText("إنجاز الخطة: 2 من 2")).toBeInTheDocument();
    expect(screen.getAllByTestId("kb06-weekly-question")).toHaveLength(5);
    expect(
      screen.getAllByTestId("kb06-weekly-question").every(
        (element) => element.dataset.sourceFile === "KB06.json",
      ),
    ).toBe(true);
    expect(
      screen.queryByText("هل يستجيب الطفل عند مناداة اسمه؟"),
    ).not.toBeInTheDocument();
    expect(submissionCount).toBe(0);
  });

  it("blocks follow-up and does not load KB06 while the active plan is incomplete", async () => {
    let questionRequestCount = 0;
    server.use(
      http.get(`${BASE}/api/v1/weekly-plans/:planId/followup-questions`, () => {
        questionRequestCount += 1;
        return HttpResponse.json(fixtureWeeklyFollowupContext);
      }),
    );

    renderWithProviders(<ReassessmentPage />, {
      authenticated: true,
      path: "/children/:childId/reassessment",
      initialEntry: "/children/child-1/reassessment?planId=plan-1",
    });

    expect(await screen.findByText("أكمل الخطة الأسبوعية أولًا")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "العودة إلى الخطة الأسبوعية" })).toBeInTheDocument();
    expect(questionRequestCount).toBe(0);
  });

  it("blocks a stale plan link after a replacement plan becomes active", async () => {
    server.use(
      http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () =>
        HttpResponse.json({ ...completedPlan, id: "replacement-plan" }),
      ),
    );

    renderWithProviders(<ReassessmentPage />, {
      authenticated: true,
      path: "/children/:childId/reassessment",
      initialEntry: "/children/child-1/reassessment?planId=plan-1",
    });

    expect(await screen.findByText("الخطة المحددة لم تعد نشطة")).toBeInTheDocument();
    expect(
      screen.queryByTestId("kb06-weekly-question"),
    ).not.toBeInTheDocument();
  });

  it("submits all KB06 answers only once under rapid duplicate clicks", async () => {
    let submissionCount = 0;
    let submittedQuestionIds: string[] = [];
    server.use(
      http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () =>
        HttpResponse.json(completedPlan),
      ),
      http.post(
        `${BASE}/api/v1/weekly-plans/:planId/followup`,
        async ({ request }) => {
          submissionCount += 1;
          const payload = (await request.json()) as {
            answers: { question_id: string }[];
          };
          submittedQuestionIds = payload.answers.map(
            (answer) => answer.question_id,
          );
          await new Promise((resolve) => setTimeout(resolve, 25));
          return HttpResponse.json(fixtureFollowup, { status: 201 });
        },
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<ReassessmentPage />, {
      authenticated: true,
      path: "/children/:childId/reassessment",
      initialEntry: "/children/child-1/reassessment?planId=plan-1",
      additionalRoutes: [
        {
          path: "/followups/:followupId",
          element: <div>نتيجة المتابعة الأسبوعية</div>,
        },
      ],
    });

    const alwaysOptions = await screen.findAllByRole("radio", { name: "دائمًا" });
    expect(alwaysOptions).toHaveLength(5);
    for (const option of alwaysOptions) {
      await user.click(option);
    }
    const submitButton = screen.getByRole("button", {
      name: "إرسال المتابعة وإنشاء خطة الأسبوع القادم",
    });
    act(() => {
      submitButton.click();
      submitButton.click();
    });

    expect(await screen.findByText("نتيجة المتابعة الأسبوعية")).toBeInTheDocument();
    await waitFor(() => expect(submissionCount).toBe(1));
    expect(submittedQuestionIds).toEqual(
      fixtureWeeklyFollowupContext.questions.map((question) => question.id),
    );
  });
});
