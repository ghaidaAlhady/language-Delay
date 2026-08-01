import { describe, expect, it } from "vitest";

import { formatArabicDate, formatArabicNumber, formatArabicPercent, formatChildAge } from "@/utils/formatArabic";

describe("formatArabicDate", () => {
  it("formats an ISO date using Arabic month names", () => {
    const formatted = formatArabicDate("2026-01-15T00:00:00Z");
    expect(formatted).toContain("يناير");
  });

  it("returns the original string for an invalid date", () => {
    expect(formatArabicDate("not-a-date")).toBe("not-a-date");
  });
});

describe("formatArabicNumber", () => {
  it("renders digits using Arabic-Indic numerals", () => {
    expect(formatArabicNumber(14)).toBe("١٤");
  });
});

describe("formatArabicPercent", () => {
  it("rounds and appends a percent sign", () => {
    expect(formatArabicPercent(85.6)).toBe("٨٦%");
  });
});

describe("formatChildAge", () => {
  it("uses the dual form for age 2", () => {
    expect(formatChildAge(2)).toBe("سنتان");
  });

  it("uses the plural form for ages 3-10", () => {
    expect(formatChildAge(4)).toBe("٤ سنوات");
  });

  it("uses the singular form for age 1", () => {
    expect(formatChildAge(1)).toBe("سنة واحدة");
  });
});
