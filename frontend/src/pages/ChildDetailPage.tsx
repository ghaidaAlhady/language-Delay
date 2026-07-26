import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ErrorState } from "@/components/ErrorState";
import { SkeletonCard } from "@/components/Skeleton";
import { useToast } from "@/components/ToastContext";
import { useAssessmentsForChild } from "@/features/assessment/useAssessments";
import { useChild, useDeleteChild } from "@/features/children/useChildren";
import { getArabicErrorMessage } from "@/utils/errorMessages";
import { formatArabicDate, formatChildAge } from "@/utils/formatArabic";

const GENDER_LABEL: Record<"male" | "female", string> = { male: "ذكر", female: "أنثى" };

export function ChildDetailPage() {
  const { childId } = useParams<{ childId: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const childQuery = useChild(childId);
  const assessmentsQuery = useAssessmentsForChild(childId);
  const deleteChild = useDeleteChild();
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  if (childQuery.isPending) return <SkeletonCard />;
  if (childQuery.isError) {
    return (
      <ErrorState
        message={getArabicErrorMessage(childQuery.error)}
        onRetry={() => void childQuery.refetch()}
      />
    );
  }

  const child = childQuery.data;
  const latestAssessment = assessmentsQuery.data?.[0];

  function handleDelete(): void {
    if (!childId) return;
    deleteChild.mutate(childId, {
      onSuccess: () => {
        showToast("تم حذف ملف الطفل.", "success");
        navigate("/children", { replace: true });
      },
      onError: (error) => {
        showToast(getArabicErrorMessage(error), "error");
        setConfirmingDelete(false);
      },
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-primary-900">ملف الطفل</h1>
          <p className="text-gray-600">{child.name}</p>
        </div>
        <div className="flex gap-2">
          <Link to={`/children/${child.id}/edit`}>
            <Button variant="outline">تعديل</Button>
          </Link>
          <Button variant="danger" onClick={() => setConfirmingDelete(true)}>
            حذف
          </Button>
        </div>
      </div>

      <Card className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="تاريخ الميلاد" value={formatArabicDate(child.date_of_birth)} />
        <Field label="العمر" value={formatChildAge(child.age_years)} />
        <Field label="الجنس" value={GENDER_LABEL[child.gender]} />
        <Field label="لغة المنزل" value={child.home_language} />
        <Field label="زار أخصائي تخاطب" value={child.has_previous_diagnosis ? "نعم" : "لا"} />
        <Field label="يستخدم سماعة" value={child.uses_hearing_aid ? "نعم" : "لا"} />
      </Card>

      {!child.is_assessment_age_eligible && (
        <Card className="border-2 border-warning-500 bg-warning-50">
          <p className="text-sm text-primary-900">
            عمر الطفل الحالي خارج النطاق المدعوم للتقييم (من سنتين إلى خمس سنوات)، لذلك لا يمكن بدء
            تقييم جديد الآن.
          </p>
        </Card>
      )}

      <div className="flex flex-wrap gap-3">
        {child.is_assessment_age_eligible && (
          <Link to={`/children/${child.id}/assessment/intro`}>
            <Button>بدء تقييم</Button>
          </Link>
        )}
        <Link to={`/children/${child.id}/weekly-plan`}>
          <Button variant="outline">الخطة الأسبوعية</Button>
        </Link>
        <Link to={`/children/${child.id}/reports`}>
          <Button variant="outline">التقارير</Button>
        </Link>
        <Link to={`/children/${child.id}/assessments`}>
          <Button variant="outline">سجل التقييمات</Button>
        </Link>
        {child.is_assessment_age_eligible &&
          (assessmentsQuery.data ?? []).some((a) => a.status === "completed") && (
            <Link to={`/children/${child.id}/reassessment`}>
              <Button variant="outline">المتابعة الأسبوعية</Button>
            </Link>
          )}
      </div>

      <Card>
        <h2 className="mb-2 font-semibold text-primary-900">آخر تقييم</h2>
        {assessmentsQuery.isPending && <p className="text-sm text-gray-500">جارٍ التحميل...</p>}
        {assessmentsQuery.data && assessmentsQuery.data.length === 0 && (
          <p className="text-sm text-gray-600">لا توجد تقييمات سابقة.</p>
        )}
        {latestAssessment && (
          <div className="text-sm text-gray-700">
            <p>التاريخ: {formatArabicDate(latestAssessment.started_at)}</p>
            <p>
              الحالة: {latestAssessment.status === "completed" ? "مكتمل" : "قيد التنفيذ"}
              {latestAssessment.overall_severity &&
                ` — النتيجة: ${latestAssessment.overall_severity}`}
            </p>
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={confirmingDelete}
        title="حذف ملف الطفل"
        description={`هل أنت متأكد من حذف ملف "${child.name}"؟ سيتم حذف جميع التقييمات والتقارير والخطط المرتبطة به نهائيًا.`}
        confirmLabel="حذف نهائي"
        isDangerous
        isConfirming={deleteChild.isPending}
        onConfirm={handleDelete}
        onCancel={() => setConfirmingDelete(false)}
      />
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-sm font-medium text-primary-900">{value}</p>
    </div>
  );
}
