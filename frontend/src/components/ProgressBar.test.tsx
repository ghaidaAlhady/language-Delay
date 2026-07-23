import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProgressBar } from "@/components/ProgressBar";

describe("ProgressBar", () => {
  it("exposes the correct ARIA progressbar values", () => {
    render(<ProgressBar value={3} max={20} label="السؤال 4 من 20" />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "3");
    expect(bar).toHaveAttribute("aria-valuemax", "20");
  });

  it("shows the provided label", () => {
    render(<ProgressBar value={3} max={20} label="السؤال 4 من 20" />);
    expect(screen.getByText("السؤال 4 من 20")).toBeInTheDocument();
  });

  it("computes the percentage text from value/max", () => {
    render(<ProgressBar value={5} max={20} />);
    expect(screen.getByText("5 من 20 (25%)")).toBeInTheDocument();
  });

  it("does not exceed 100% even if value > max", () => {
    render(<ProgressBar value={25} max={20} />);
    expect(screen.getByText("25 من 20 (100%)")).toBeInTheDocument();
  });
});
