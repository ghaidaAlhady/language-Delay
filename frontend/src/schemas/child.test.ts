import { describe, expect, it } from "vitest";

import { childFormSchema, childResponseToFormValues } from "@/schemas/child";
import type { ChildResponse } from "@/types/api";

const validChild = {
  name: "سارة",
  dateOfBirth: "2022-01-01",
  gender: "female" as const,
  homeLanguage: "ar",
  hasPreviousDiagnosis: false,
  hasHearingProblems: false,
  usesHearingAid: false,
};

describe("childFormSchema", () => {
  it("accepts valid input", () => {
    expect(childFormSchema.safeParse(validChild).success).toBe(true);
  });

  it("rejects an empty name", () => {
    expect(childFormSchema.safeParse({ ...validChild, name: "" }).success).toBe(false);
  });

  it("rejects a future date of birth", () => {
    const future = new Date();
    future.setFullYear(future.getFullYear() + 1);
    const result = childFormSchema.safeParse({
      ...validChild,
      dateOfBirth: future.toISOString().slice(0, 10),
    });
    expect(result.success).toBe(false);
  });

  it("rejects a missing gender", () => {
    const { gender: _gender, ...withoutGender } = validChild;
    expect(childFormSchema.safeParse(withoutGender).success).toBe(false);
  });

  it("rejects notes longer than 2000 characters", () => {
    const result = childFormSchema.safeParse({ ...validChild, notes: "a".repeat(2001) });
    expect(result.success).toBe(false);
  });
});

describe("childResponseToFormValues", () => {
  it("maps every backend field to its camelCase form field", () => {
    const child: ChildResponse = {
      id: "c1",
      name: "سارة",
      date_of_birth: "2022-01-01",
      gender: "female",
      home_language: "ar",
      has_previous_diagnosis: true,
      previous_diagnosis_details: "تفاصيل",
      has_hearing_problems: true,
      uses_hearing_aid: false,
      notes: "ملاحظة",
      age_years: 4,
      is_assessment_age_eligible: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };

    expect(childResponseToFormValues(child)).toEqual({
      name: "سارة",
      dateOfBirth: "2022-01-01",
      gender: "female",
      homeLanguage: "ar",
      hasPreviousDiagnosis: true,
      previousDiagnosisDetails: "تفاصيل",
      hasHearingProblems: true,
      usesHearingAid: false,
      notes: "ملاحظة",
    });
  });

  it("maps null optional fields to empty strings", () => {
    const child: ChildResponse = {
      id: "c1",
      name: "سارة",
      date_of_birth: "2022-01-01",
      gender: "female",
      home_language: "ar",
      has_previous_diagnosis: false,
      previous_diagnosis_details: null,
      has_hearing_problems: false,
      uses_hearing_aid: false,
      notes: null,
      age_years: 4,
      is_assessment_age_eligible: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };

    const values = childResponseToFormValues(child);
    expect(values.previousDiagnosisDetails).toBe("");
    expect(values.notes).toBe("");
  });
});
