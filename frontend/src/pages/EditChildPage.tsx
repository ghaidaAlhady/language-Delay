import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Card } from "@/components/Card";
import { ErrorState } from "@/components/ErrorState";
import { Skeleton } from "@/components/Skeleton";
import { useToast } from "@/components/ToastContext";
import { ChildForm } from "@/features/children/ChildForm";
import { useChild, useUpdateChild } from "@/features/children/useChildren";
import { childResponseToFormValues } from "@/schemas/child";
import type { ChildCreateRequest } from "@/types/api";
import { getArabicErrorMessage } from "@/utils/errorMessages";

export function EditChildPage() {
  const { childId } = useParams<{ childId: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const childQuery = useChild(childId);
  const updateChild = useUpdateChild(childId ?? "");
  const [serverError, setServerError] = useState<string | null>(null);

  function handleSubmit(payload: ChildCreateRequest): void {
    setServerError(null);
    updateChild.mutate(payload, {
      onSuccess: () => {
        showToast("تم حفظ التعديلات بنجاح ✓", "success");
        navigate(`/children/${childId}`, { replace: true });
      },
      onError: (error) => {
        setServerError(getArabicErrorMessage(error));
      },
    });
  }

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="mb-6 text-2xl font-bold text-primary-900">تعديل ملف الطفل</h1>
      <Card>
        {childQuery.isPending && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        )}
        {childQuery.isError && (
          <ErrorState
            message={getArabicErrorMessage(childQuery.error)}
            onRetry={() => void childQuery.refetch()}
          />
        )}
        {childQuery.data && (
          <ChildForm
            defaultValues={childResponseToFormValues(childQuery.data)}
            submitLabel="حفظ التعديلات"
            isSubmitting={updateChild.isPending}
            serverError={serverError}
            onSubmit={handleSubmit}
          />
        )}
      </Card>
    </div>
  );
}
