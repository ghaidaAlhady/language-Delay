import { HttpResponse, http } from "msw";
import { act } from "react";
import { describe, expect, it } from "vitest";

import { AssessmentResultPage } from "@/pages/AssessmentResultPage";
import { fixtureAssessmentCompleted, fixtureFollowup } from "@/tests/fixtures";
import { server } from "@/tests/mocks/server";
import { renderWithProviders, screen, waitFor } from "@/tests/test-utils";

const BASE = import.meta.env.VITE_API_BASE_URL;

describe("AssessmentResultPage", () => {
  it("renders the overall severity, strengths, support needs, and per-domain results", async () => {
    renderWithProviders(<AssessmentResultPage />, {
      authenticated: true,
      path: "/assessments/:assessmentId/result",
      initialEntry: "/assessments/assessment-1/result",
    });

    expect(await screen.findByText("النتيجة الكلية")).toBeInTheDocument();
    expect(screen.getAllByText("طبيعي").length).toBeGreaterThan(0);
    expect(screen.getByText(/الاستجابة للاسم/)).toBeInTheDocument();
    expect(screen.getByText("لا توجد مهارات تحتاج دعمًا إضافيًا حاليًا.")).toBeInTheDocument();
    expect(screen.getByText("اللغة الاستقبالية")).toBeInTheDocument();
  });

  it("shows the generate-report and generate-plan actions", async () => {
    renderWithProviders(<AssessmentResultPage />, {
      authenticated: true,
      path: "/assessments/:assessmentId/result",
      initialEntry: "/assessments/assessment-1/result",
    });

    expect(await screen.findByRole("button", { name: "عرض التقرير" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "إنشاء الخطة الأسبوعية" })).toBeInTheDocument();
  });

  it("submits a weekly follow-up only once under rapid duplicate clicks", async () => {
    const currentAssessment = {
      ...fixtureAssessmentCompleted,
      id: "assessment-2",
      completed_at: "2026-01-08T00:00:00Z",
    };
    let submissionCount = 0;
    server.use(
      http.get(`${BASE}/api/v1/assessments/:assessmentId`, () =>
        HttpResponse.json(currentAssessment),
      ),
      http.get(`${BASE}/api/v1/children/:childId/assessments`, () =>
        HttpResponse.json([currentAssessment, fixtureAssessmentCompleted]),
      ),
      http.post(`${BASE}/api/v1/assessments/:assessmentId/followup`, async () => {
        submissionCount += 1;
        await new Promise((resolve) => setTimeout(resolve, 25));
        return HttpResponse.json(fixtureFollowup, { status: 201 });
      }),
    );

    renderWithProviders(<AssessmentResultPage />, {
      authenticated: true,
      path: "/assessments/:assessmentId/result",
      initialEntry: "/assessments/assessment-2/result",
      additionalRoutes: [{ path: "/followups/:followupId", element: <div>نتيجة المتابعة</div> }],
    });

    const followupButton = await screen.findByRole("button", {
      name: "إكمال المتابعة الأسبوعية",
    });
    act(() => {
      followupButton.click();
      followupButton.click();
    });

    expect(await screen.findByText("نتيجة المتابعة")).toBeInTheDocument();
    await waitFor(() => expect(submissionCount).toBe(1));
  });
});
