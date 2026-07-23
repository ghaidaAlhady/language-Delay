import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Card } from "@/components/Card";
import { useToast } from "@/components/ToastContext";
import { ChildForm } from "@/features/children/ChildForm";
import { useCreateChild } from "@/features/children/useChildren";
import type { ChildCreateRequest } from "@/types/api";
import { getArabicErrorMessage } from "@/utils/errorMessages";

export function AddChildPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const createChild = useCreateChild();
  const [serverError, setServerError] = useState<string | null>(null);

  function handleSubmit(payload: ChildCreateRequest): void {
    setServerError(null);
    createChild.mutate(payload, {
      onSuccess: (child) => {
        showToast("تمت إضافة الطفل بنجاح ✓", "success");
        navigate(`/children/${child.id}`, { replace: true });
      },
      onError: (error) => {
        setServerError(getArabicErrorMessage(error));
      },
    });
  }

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="mb-6 text-2xl font-bold text-primary-900">إضافة طفل</h1>
      <Card>
        <ChildForm
          submitLabel="حفظ"
          isSubmitting={createChild.isPending}
          serverError={serverError}
          onSubmit={handleSubmit}
        />
      </Card>
    </div>
  );
}
