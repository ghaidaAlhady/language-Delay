import { z } from "zod";

import type { ChildResponse } from "@/types/api";

// Mirrors backend/app/schemas/child.py (ChildCreateRequest) field-for-field.
export const childFormSchema = z.object({
  name: z.string().min(1, "اسم الطفل مطلوب.").max(255, "الاسم طويل جدًا."),
  dateOfBirth: z
    .string()
    .min(1, "تاريخ الميلاد مطلوب.")
    .refine((value) => new Date(value) <= new Date(), "تاريخ الميلاد لا يمكن أن يكون في المستقبل."),
  gender: z.enum(["male", "female"], { message: "الجنس مطلوب." }),
  homeLanguage: z.string().min(1, "لغة المنزل مطلوبة.").max(50, "القيمة طويلة جدًا."),
  hasPreviousDiagnosis: z.boolean(),
  previousDiagnosisDetails: z.string().max(2000, "النص طويل جدًا.").optional(),
  hasHearingProblems: z.boolean(),
  usesHearingAid: z.boolean(),
  notes: z.string().max(2000, "النص طويل جدًا.").optional(),
});

export type ChildFormValues = z.infer<typeof childFormSchema>;

export function childResponseToFormValues(child: ChildResponse): ChildFormValues {
  return {
    name: child.name,
    dateOfBirth: child.date_of_birth,
    gender: child.gender,
    homeLanguage: child.home_language,
    hasPreviousDiagnosis: child.has_previous_diagnosis,
    previousDiagnosisDetails: child.previous_diagnosis_details ?? "",
    hasHearingProblems: child.has_hearing_problems,
    usesHearingAid: child.uses_hearing_aid,
    notes: child.notes ?? "",
  };
}
