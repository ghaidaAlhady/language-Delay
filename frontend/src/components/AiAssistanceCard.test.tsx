import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AiAssistanceCard } from "@/components/AiAssistanceCard";
import { fixtureAIAssistance } from "@/tests/fixtures";
import { render, screen } from "@/tests/test-utils";

describe("AiAssistanceCard", () => {
  it("shows a non-blocking loading state", () => {
    render(
      <AiAssistanceCard
        heading="شرح مبسط للنتيجة"
        data={undefined}
        isPending
        isError={false}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("جارٍ إعداد الصياغة المساندة");
  });

  it("labels Gemini wording and renders grounded content", async () => {
    render(
      <AiAssistanceCard
        heading="شرح مبسط للنتيجة"
        data={fixtureAIAssistance}
        isPending={false}
        isError={false}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText("صياغة مساندة بالذكاء الاصطناعي")).toBeInTheDocument();
    expect(screen.getByText(fixtureAIAssistance.content.summary)).toBeInTheDocument();

    // No raw comma-separated source IDs as primary card content.
    expect(screen.queryByText(/المصادر المعتمدة: A001/)).not.toBeInTheDocument();
    // The compact, collapsed-by-default source disclosure instead.
    const disclosure = screen.getByText("المصادر المعتمدة (1)");
    expect(disclosure.closest("details")).not.toHaveAttribute("open");
    expect(screen.getByText("أكمل الجملة")).not.toBeVisible();
    await userEvent.setup().click(disclosure);
    expect(screen.getByText("أكمل الجملة")).toBeVisible();
    expect(screen.getAllByTitle("A001").length).toBeGreaterThan(0);
  });

  it("labels deterministic fallback and retries retryable failures", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(
      <AiAssistanceCard
        heading="ملخص الخطة الأسبوعية"
        data={{
          ...fixtureAIAssistance,
          generation_source: "deterministic_fallback",
          fallback_reason: "timeout",
        }}
        isPending={false}
        isError={false}
        onRetry={onRetry}
      />,
    );

    expect(screen.getByText("ملخص آمن من النظام")).toBeInTheDocument();
    expect(screen.getByText(/لم تتوفر صياغة الذكاء الاصطناعي/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "إعادة المحاولة" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });


  it("shows a busy state during manual refetch so retry cannot be clicked repeatedly", () => {
    render(
      <AiAssistanceCard
        heading="ملخص الخطة الأسبوعية"
        data={{
          ...fixtureAIAssistance,
          generation_source: "deterministic_fallback",
          fallback_reason: "provider_unavailable",
        }}
        isPending={false}
        isFetching
        isError={false}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("جارٍ إعداد الصياغة المساندة");
    expect(screen.queryByRole("button", { name: "إعادة المحاولة" })).not.toBeInTheDocument();
  });

  it("keeps disabled fallback useful without an ineffective retry", () => {
    render(
      <AiAssistanceCard
        heading="ملخص تقدم الأسبوع"
        data={{
          ...fixtureAIAssistance,
          generation_source: "deterministic_fallback",
          fallback_reason: "disabled",
        }}
        isPending={false}
        isError={false}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText("ملخص آمن من النظام")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "إعادة المحاولة" })).not.toBeInTheDocument();
  });

  it("shows a generic network error and retry", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(
      <AiAssistanceCard
        heading="شرح مبسط للنتيجة"
        data={undefined}
        isPending={false}
        isError
        onRetry={onRetry}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("تظل النتيجة الحتمية أعلاه هي المرجع");
    await user.click(screen.getByRole("button", { name: "إعادة المحاولة" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
