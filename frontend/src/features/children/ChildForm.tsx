import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { Button } from "@/components/Button";
import { CheckboxField } from "@/components/CheckboxField";
import { SelectField } from "@/components/SelectField";
import { TextField } from "@/components/TextField";
import { childFormSchema, type ChildFormValues } from "@/schemas/child";
import type { ChildCreateRequest } from "@/types/api";

interface ChildFormProps {
  defaultValues?: Partial<ChildFormValues>;
  submitLabel: string;
  isSubmitting: boolean;
  serverError: string | null;
  onSubmit: (payload: ChildCreateRequest) => void;
}

export function ChildForm({ defaultValues, submitLabel, isSubmitting, serverError, onSubmit }: ChildFormProps) {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ChildFormValues>({
    resolver: zodResolver(childFormSchema),
    defaultValues: {
      hasPreviousDiagnosis: false,
      hasHearingProblems: false,
      usesHearingAid: false,
      homeLanguage: "ar",
      ...defaultValues,
    },
  });

  const hasHearingProblems = watch("hasHearingProblems");

  function submit(values: ChildFormValues): void {
    onSubmit({
      name: values.name,
      date_of_birth: values.dateOfBirth,
      gender: values.gender,
      home_language: values.homeLanguage,
      has_previous_diagnosis: values.hasPreviousDiagnosis,
      previous_diagnosis_details: values.previousDiagnosisDetails || null,
      has_hearing_problems: values.hasHearingProblems,
      uses_hearing_aid: values.usesHearingAid,
      notes: values.notes || null,
    });
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={(e) => void handleSubmit(submit)(e)} noValidate>
      <TextField label="اسم الطفل" error={errors.name?.message} {...register("name")} />

      <TextField
        label="تاريخ الميلاد"
        type="date"
        error={errors.dateOfBirth?.message}
        {...register("dateOfBirth")}
      />

      <SelectField
        label="الجنس"
        placeholder="اختر الجنس"
        options={[
          { value: "male", label: "ذكر" },
          { value: "female", label: "أنثى" },
        ]}
        error={errors.gender?.message}
        {...register("gender")}
      />

      <TextField
        label="لغة المنزل"
        error={errors.homeLanguage?.message}
        {...register("homeLanguage")}
      />

      <CheckboxField label="هل سبق مراجعة أخصائي تخاطب؟" {...register("hasPreviousDiagnosis")} />
      <TextField
        label="تفاصيل إضافية (اختياري)"
        error={errors.previousDiagnosisDetails?.message}
        {...register("previousDiagnosisDetails")}
      />

      <CheckboxField label="هل يعاني الطفل من مشاكل في السمع؟" {...register("hasHearingProblems")} />
      {hasHearingProblems && (
        <CheckboxField label="هل يستخدم سماعة؟" {...register("usesHearingAid")} />
      )}

      <TextField label="ملاحظات (اختياري)" error={errors.notes?.message} {...register("notes")} />

      {serverError && (
        <p role="alert" className="text-sm text-danger-600">
          {serverError}
        </p>
      )}

      <Button type="submit" isLoading={isSubmitting} className="mt-2">
        {submitLabel}
      </Button>
    </form>
  );
}
