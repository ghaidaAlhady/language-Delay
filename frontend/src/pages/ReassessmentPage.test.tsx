import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { ReassessmentPage } from "@/pages/ReassessmentPage";
import { fixtureWeeklyPlan } from "@/tests/fixtures";
import { server } from "@/tests/mocks/server";
import { renderWithProviders, screen } from "@/tests/test-utils";

const BASE = import.meta.env.VITE_API_BASE_URL;

describe("ReassessmentPage", () => {
  it("shows the child and matching active-plan context before weekly follow-up", async () => {
    renderWithProviders(<ReassessmentPage />, {
      authenticated: true,
      path: "/children/:childId/reassessment",
      initialEntry: "/children/child-1/reassessment",
    });

    expect(await screen.findByRole("heading", { name: "المتابعة الأسبوعية" })).toBeInTheDocument();
    expect(screen.getByText("الطفل: سارة")).toBeInTheDocument();
    expect(screen.getByText(/الخطة النشطة منذ/)).toBeInTheDocument();
    expect(screen.getByText(/إنجاز الخطة/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ابدأ أسئلة المتابعة الأسبوعية" })).toBeEnabled();
  });

  it("blocks follow-up when there is no active weekly plan", async () => {
    server.use(
      http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () =>
        HttpResponse.json(
          { error: { code: "not_found", message: "no active plan" } },
          { status: 404 },
        ),
      ),
    );

    renderWithProviders(<ReassessmentPage />, {
      authenticated: true,
      path: "/children/:childId/reassessment",
      initialEntry: "/children/child-1/reassessment",
      additionalRoutes: [
        {
          path: "/assessments/:assessmentId/result",
          element: <div>نتيجة التقييم</div>,
        },
      ],
    });

    expect(await screen.findByText("لا توجد خطة أسبوعية نشطة للمتابعة")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "ابدأ أسئلة المتابعة الأسبوعية" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "العودة إلى نتيجة التقييم" })).toBeInTheDocument();
  });

  it("blocks follow-up when the active plan belongs to a different assessment", async () => {
    server.use(
      http.get(`${BASE}/api/v1/children/:childId/weekly-plan`, () =>
        HttpResponse.json({
          ...fixtureWeeklyPlan,
          assessment_id: "different-assessment",
        }),
      ),
    );

    renderWithProviders(<ReassessmentPage />, {
      authenticated: true,
      path: "/children/:childId/reassessment",
      initialEntry: "/children/child-1/reassessment",
    });

    expect(await screen.findByText("الخطة الأسبوعية لا تطابق آخر تقييم")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "ابدأ أسئلة المتابعة الأسبوعية" }),
    ).not.toBeInTheDocument();
  });
});
