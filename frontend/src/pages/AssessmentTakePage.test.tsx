import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { AssessmentTakePage } from "@/pages/AssessmentTakePage";
import { fixtureAssessmentCompleted, fixtureAssessmentInProgress, fixtureQuestions } from "@/tests/fixtures";
import { server } from "@/tests/mocks/server";
import { renderWithProviders, screen, waitFor } from "@/tests/test-utils";

const BASE = import.meta.env.VITE_API_BASE_URL;

describe("AssessmentTakePage", () => {
  it("shows the first question and a progress indicator for a fresh assessment", async () => {
    server.use(
      http.get(`${BASE}/api/v1/assessments/:id`, () => HttpResponse.json(fixtureAssessmentInProgress)),
    );
    renderWithProviders(<AssessmentTakePage />, {
      authenticated: true,
      path: "/assessments/:assessmentId/take",
      initialEntry: "/assessments/assessment-1/take",
    });

    expect(await screen.findByText(fixtureQuestions[0]!.question)).toBeInTheDocument();
    expect(screen.getByText("السؤال 1 من 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "التالي" })).toBeDisabled();
  });

  it("resumes at answered_count when re-entering a partially-answered assessment", async () => {
    server.use(
      http.get(`${BASE}/api/v1/assessments/:id`, () =>
        HttpResponse.json({ ...fixtureAssessmentInProgress, answered_count: 1 }),
      ),
    );
    renderWithProviders(<AssessmentTakePage />, {
      authenticated: true,
      path: "/assessments/:assessmentId/take",
      initialEntry: "/assessments/assessment-1/take",
    });

    expect(await screen.findByText(fixtureQuestions[1]!.question)).toBeInTheDocument();
    expect(screen.getByText("السؤال 2 من 2")).toBeInTheDocument();
  });

  it("enables Next only after a response is selected, and submits it", async () => {
    server.use(
      http.get(`${BASE}/api/v1/assessments/:id`, () => HttpResponse.json(fixtureAssessmentInProgress)),
    );
    let submittedBody: unknown = null;
    server.use(
      http.post(`${BASE}/api/v1/assessments/:id/answers`, async ({ request }) => {
        submittedBody = await request.json();
        return HttpResponse.json({ ...fixtureAssessmentInProgress, answered_count: 1 });
      }),
    );

    const user = userEvent.setup();
    renderWithProviders(<AssessmentTakePage />, {
      authenticated: true,
      path: "/assessments/:assessmentId/take",
      initialEntry: "/assessments/assessment-1/take",
    });

    await screen.findByText(fixtureQuestions[0]!.question);
    const nextButton = screen.getByRole("button", { name: "التالي" });
    expect(nextButton).toBeDisabled();

    await user.click(screen.getByRole("radio", { name: "دائمًا" }));
    expect(nextButton).toBeEnabled();
    await user.click(nextButton);

    expect(await screen.findByText(fixtureQuestions[1]!.question)).toBeInTheDocument();
    expect(submittedBody).toEqual({ answers: [{ question_id: "Q001", response: "always" }] });
  });

  it("submits the final answer and completes the assessment only once under rapid duplicate clicks", async () => {
    server.use(
      http.get(`${BASE}/api/v1/assessments/:id`, () =>
        HttpResponse.json({ ...fixtureAssessmentInProgress, answered_count: 1 }),
      ),
    );
    let submitCount = 0;
    let completeCount = 0;
    server.use(
      http.post(`${BASE}/api/v1/assessments/:id/answers`, async () => {
        submitCount += 1;
        return HttpResponse.json({ ...fixtureAssessmentInProgress, answered_count: 2 });
      }),
      http.post(`${BASE}/api/v1/assessments/:id/complete`, async () => {
        completeCount += 1;
        return HttpResponse.json(fixtureAssessmentCompleted);
      }),
    );

    const user = userEvent.setup();
    renderWithProviders(<AssessmentTakePage />, {
      authenticated: true,
      path: "/assessments/:assessmentId/take",
      initialEntry: "/assessments/assessment-1/take",
    });

    await screen.findByText(fixtureQuestions[1]!.question);
    await user.click(screen.getByRole("radio", { name: "دائمًا" }));
    const finishButton = screen.getByRole("button", { name: "عرض النتائج" });

    // Fire two rapid clicks on the same still-enabled element, simulating a
    // duplicate click landing before React commits the disabled state.
    finishButton.click();
    finishButton.click();

    await waitFor(() => expect(completeCount).toBe(1));
    expect(submitCount).toBe(1);
  });
});
