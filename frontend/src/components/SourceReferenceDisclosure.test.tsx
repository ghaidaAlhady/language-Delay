import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { SourceReferenceDisclosure } from "@/components/SourceReferenceDisclosure";
import { render, screen } from "@/tests/test-utils";

describe("SourceReferenceDisclosure", () => {
  it("renders nothing when there are no source ids", () => {
    const { container } = render(
      <SourceReferenceDisclosure sourceIds={[]} sourceReferences={[]} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("is collapsed by default and shows the count", () => {
    render(
      <SourceReferenceDisclosure
        sourceIds={["A001", "A002"]}
        sourceReferences={[
          { source_id: "A001", label_ar: "أكمل الجملة", category: "نشاط معتمد" },
          { source_id: "A002", label_ar: "لعبة الإشارة", category: "نشاط معتمد" },
        ]}
      />,
    );

    const summary = screen.getByText("المصادر المعتمدة (2)");
    expect(summary.closest("details")).not.toHaveAttribute("open");
    // Native <details> keeps its children in the DOM even when collapsed
    // (only hidden via browser-native rendering) — assert visibility, not
    // DOM presence.
    expect(screen.getByText("أكمل الجملة")).not.toBeVisible();
  });

  it("expands via keyboard/click to show human-readable labels with the raw id as secondary text", async () => {
    const user = userEvent.setup();
    render(
      <SourceReferenceDisclosure
        sourceIds={["A001"]}
        sourceReferences={[{ source_id: "A001", label_ar: "أكمل الجملة", category: "نشاط معتمد" }]}
      />,
    );

    const summary = screen.getByText("المصادر المعتمدة (1)");
    await user.click(summary);

    expect(summary.closest("details")).toHaveAttribute("open");
    expect(screen.getByText("أكمل الجملة")).toBeInTheDocument();
    const idText = screen.getByTitle("A001");
    expect(idText).toHaveTextContent("A001");
  });

  it("the summary is natively keyboard-focusable (no tabindex trap)", () => {
    // Native <summary> is keyboard-operable (focus + Enter/Space toggles it)
    // by the HTML spec with no JS required — jsdom does not simulate the
    // browser's default Enter-on-<summary> toggle action, so this test
    // confirms the piece under this component's control: nothing here
    // blocks keyboard focus (no negative tabindex, no aria-hidden, etc.).
    render(
      <SourceReferenceDisclosure
        sourceIds={["A001"]}
        sourceReferences={[{ source_id: "A001", label_ar: "أكمل الجملة", category: "نشاط معتمد" }]}
      />,
    );

    const summary = screen.getByText("المصادر المعتمدة (1)");
    summary.focus();
    expect(summary).toHaveFocus();
  });

  it("falls back to a neutral label when no reference resolves", async () => {
    const user = userEvent.setup();
    render(<SourceReferenceDisclosure sourceIds={["UNKNOWN-1"]} sourceReferences={[]} />);

    await user.click(screen.getByText("المصادر المعتمدة (1)"));

    expect(screen.getByText("مصدر معتمد")).toBeInTheDocument();
    expect(screen.getByTitle("UNKNOWN-1")).toBeInTheDocument();
  });
});
