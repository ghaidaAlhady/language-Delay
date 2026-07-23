import userEvent from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ResponseScale } from "@/features/assessment/ResponseScale";

describe("ResponseScale", () => {
  it("renders all five response options", () => {
    render(<ResponseScale value={null} onChange={vi.fn()} />);
    for (const label of ["دائمًا", "غالبًا", "أحيانًا", "نادرًا", "أبدًا"]) {
      expect(screen.getByRole("radio", { name: label })).toBeInTheDocument();
    }
  });

  it("marks the selected value as checked", () => {
    render(<ResponseScale value="often" onChange={vi.fn()} />);
    expect(screen.getByRole("radio", { name: "غالبًا" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByRole("radio", { name: "دائمًا" })).toHaveAttribute("aria-checked", "false");
  });

  it("calls onChange with the selected value's response key", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ResponseScale value={null} onChange={onChange} />);

    await user.click(screen.getByRole("radio", { name: "أبدًا" }));
    expect(onChange).toHaveBeenCalledWith("never");
  });

  it("disables all options when disabled is true", () => {
    render(<ResponseScale value={null} onChange={vi.fn()} disabled />);
    for (const radio of screen.getAllByRole("radio")) {
      expect(radio).toBeDisabled();
    }
  });
});
