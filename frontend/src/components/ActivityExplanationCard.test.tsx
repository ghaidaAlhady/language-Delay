import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ActivityExplanationCard } from "@/components/ActivityExplanationCard";
import { fixtureActivityExplanation } from "@/tests/fixtures";
import { render, screen } from "@/tests/test-utils";

describe("ActivityExplanationCard", () => {
  it("shows a non-blocking loading state", () => {
    render(
      <ActivityExplanationCard data={undefined} isPending isError={false} onRetry={vi.fn()} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("جارٍ إعداد شرح مبسّط للنشاط");
  });

  it("renders the explanation, purpose, steps, example dialogue, and alternative", () => {
    render(
      <ActivityExplanationCard
        data={fixtureActivityExplanation}
        isPending={false}
        isError={false}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText("شرح بالذكاء الاصطناعي")).toBeInTheDocument();
    expect(screen.getByText(fixtureActivityExplanation.content.simple_explanation_ar)).toBeInTheDocument();
    expect(screen.getByText(fixtureActivityExplanation.content.purpose_ar)).toBeInTheDocument();
    for (const step of fixtureActivityExplanation.content.steps_ar) {
      expect(screen.getByText(new RegExp(step))).toBeInTheDocument();
    }
    expect(
      screen.getByText(fixtureActivityExplanation.content.example_dialogue.parent_text),
    ).toBeInTheDocument();
    expect(
      screen.getByText(fixtureActivityExplanation.content.example_dialogue.example_child_response),
    ).toBeInTheDocument();
    expect(screen.getByText(fixtureActivityExplanation.content.alternative_ar)).toBeInTheDocument();
  });

  it("labels a deterministic fallback explanation", () => {
    render(
      <ActivityExplanationCard
        data={{
          ...fixtureActivityExplanation,
          generation_source: "deterministic_fallback",
          fallback_reason: "timeout",
        }}
        isPending={false}
        isError={false}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText("شرح آمن من النظام")).toBeInTheDocument();
  });


  it("offers one manual retry for a temporary fallback and blocks it while refetching", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    const fallback = {
      ...fixtureActivityExplanation,
      generation_source: "deterministic_fallback" as const,
      fallback_reason: "provider_unavailable" as const,
    };

    const { rerender } = render(
      <ActivityExplanationCard
        data={fallback}
        isPending={false}
        isFetching={false}
        isError={false}
        onRetry={onRetry}
      />,
    );

    await user.click(screen.getByRole("button", { name: "إعادة المحاولة بالذكاء الاصطناعي" }));
    expect(onRetry).toHaveBeenCalledOnce();

    rerender(
      <ActivityExplanationCard
        data={fallback}
        isPending={false}
        isFetching
        isError={false}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("جارٍ إعداد شرح مبسّط للنشاط");
    expect(
      screen.queryByRole("button", { name: "إعادة المحاولة بالذكاء الاصطناعي" }),
    ).not.toBeInTheDocument();
  });

  it("shows a safe generic error state with retry", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(<ActivityExplanationCard data={undefined} isPending={false} isError onRetry={onRetry} />);

    expect(screen.getByRole("alert")).toHaveTextContent("تعذر تحميل الشرح");
    await user.click(screen.getByRole("button", { name: "إعادة المحاولة" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
