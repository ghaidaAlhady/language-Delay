import { describe, expect, it } from "vitest";

import { AssessmentResultPage } from "@/pages/AssessmentResultPage";
import { renderWithProviders, screen } from "@/tests/test-utils";

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
    expect(
      screen.getByText("المتابعة: إعادة التقييم بعد أسبوع وتحديث الخطة"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/درجة الثقة/)).not.toBeInTheDocument();
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

});
