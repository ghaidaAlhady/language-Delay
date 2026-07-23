import { describe, expect, it } from "vitest";

import { ReportPage } from "@/pages/ReportPage";
import { renderWithProviders, screen } from "@/tests/test-utils";

describe("ReportPage", () => {
  it("renders the report number, summary, and non-diagnostic disclaimer", async () => {
    renderWithProviders(<ReportPage />, {
      authenticated: true,
      path: "/reports/:reportId",
      initialEntry: "/reports/report-1",
    });

    expect(await screen.findByText("REP-0001")).toBeInTheDocument();
    expect(screen.getByText(/أظهر التقييم أن الطفل يحقق المهارات اللغوية المتوقعة/)).toBeInTheDocument();
    expect(screen.getByText(/لا يغني عن التقييم أو العلاج من قبل أخصائي تخاطب مؤهل/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "تحميل PDF" })).toBeInTheDocument();
  });
});
