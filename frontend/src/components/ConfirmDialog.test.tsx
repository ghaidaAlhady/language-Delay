import userEvent from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ConfirmDialog } from "@/components/ConfirmDialog";

describe("ConfirmDialog", () => {
  it("renders the title and description when open", () => {
    render(
      <ConfirmDialog
        open
        title="حذف ملف الطفل"
        description="هل أنت متأكد؟"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("حذف ملف الطفل")).toBeInTheDocument();
    expect(screen.getByText("هل أنت متأكد؟")).toBeInTheDocument();
  });

  it("calls onConfirm when the confirm button is clicked", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        open
        title="حذف"
        description="متأكد؟"
        confirmLabel="حذف نهائي"
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    );
    await user.click(screen.getByRole("button", { name: "حذف نهائي" }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("calls onCancel when the cancel button is clicked", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(
      <ConfirmDialog open title="حذف" description="متأكد؟" onConfirm={vi.fn()} onCancel={onCancel} />,
    );
    await user.click(screen.getByRole("button", { name: "إلغاء" }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("shows a loading state on the confirm button while isConfirming", () => {
    render(
      <ConfirmDialog
        open
        title="حذف"
        description="متأكد؟"
        confirmLabel="حذف نهائي"
        isConfirming
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /حذف نهائي/ })).toBeDisabled();
  });
});
