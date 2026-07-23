import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChildForm } from "@/features/children/ChildForm";
import { render, screen } from "@/tests/test-utils";

describe("ChildForm", () => {
  it("shows a validation error when the name is empty", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ChildForm submitLabel="حفظ" isSubmitting={false} serverError={null} onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: "حفظ" }));

    expect(await screen.findByText("اسم الطفل مطلوب.")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("maps camelCase form values to the snake_case API payload on submit", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ChildForm submitLabel="حفظ" isSubmitting={false} serverError={null} onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText("اسم الطفل"), "سارة");
    await user.type(screen.getByLabelText("تاريخ الميلاد"), "2022-01-01");
    await user.selectOptions(screen.getByLabelText("الجنس"), "female");
    await user.click(screen.getByRole("button", { name: "حفظ" }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "سارة",
        date_of_birth: "2022-01-01",
        gender: "female",
        has_previous_diagnosis: false,
      }),
    );
  });

  it("reveals the hearing-aid question only when hearing problems is checked", async () => {
    const user = userEvent.setup();
    render(<ChildForm submitLabel="حفظ" isSubmitting={false} serverError={null} onSubmit={vi.fn()} />);

    expect(screen.queryByLabelText("هل يستخدم سماعة؟")).not.toBeInTheDocument();
    await user.click(screen.getByLabelText("هل يعاني الطفل من مشاكل في السمع؟"));
    expect(screen.getByLabelText("هل يستخدم سماعة؟")).toBeInTheDocument();
  });

  it("shows the submitting state and disables interaction", () => {
    render(<ChildForm submitLabel="حفظ" isSubmitting serverError={null} onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: /حفظ/ })).toBeDisabled();
  });

  it("shows a server error message when provided", () => {
    render(
      <ChildForm submitLabel="حفظ" isSubmitting={false} serverError="حدث خطأ غير متوقع." onSubmit={vi.fn()} />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("حدث خطأ غير متوقع.");
  });
});
