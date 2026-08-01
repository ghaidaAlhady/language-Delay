import { useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { ErrorState } from "@/components/ErrorState";
import { SkeletonCard } from "@/components/Skeleton";
import { useAssessmentsForChild, useStartAssessment } from "@/features/assessment/useAssessments";
import { useChild } from "@/features/children/useChildren";
import { getArabicErrorMessage } from "@/utils/errorMessages";

export function AssessmentIntroPage() {
  const { childId } = useParams<{ childId: string }>();
  const navigate = useNavigate();
  const childQuery = useChild(childId);
  const assessmentsQuery = useAssessmentsForChild(childId);
  const startAssessment = useStartAssessment();

  const inProgress = assessmentsQuery.data?.find((a) => a.status === "in_progress");

  function handleStart(): void {
    if (inProgress) {
      navigate(`/assessments/${inProgress.id}/take`);
      return;
    }
    if (!childId) return;
    startAssessment.mutate(childId, {
      onSuccess: (assessment) => navigate(`/assessments/${assessment.id}/take`),
    });
  }

  if (childQuery.isPending || assessmentsQuery.isPending) return <SkeletonCard />;
  if (childQuery.isError) {
    return <ErrorState message={getArabicErrorMessage(childQuery.error)} onRetry={() => void childQuery.refetch()} />;
  }

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-1 text-2xl font-bold text-primary-900">التقييم الأولي</h1>
      <p className="mb-6 text-gray-600">التقييم لـ {childQuery.data?.name}</p>

      <Card className="flex flex-col gap-4">
        <p className="text-gray-700">
          سيتم طرح مجموعة من الأسئلة المناسبة لعمر الطفل لتقديم تقييم أولي لمؤشرات التأخر اللغوي.
          يستغرق التقييم عادة من 5 إلى 10 دقائق.
        </p>
        <p className="text-gray-700">
          للحصول على أدق النتائج، يرجى الإجابة عن جميع الأسئلة بصدق بناءً على سلوك الطفل المعتاد.
        </p>
        <div className="rounded-xl bg-warning-50 p-4 text-sm text-primary-900">
          هذا التقييم لا يُعد تشخيصًا طبيًا، بل هو أداة مساعدة للكشف المبكر، ولا يغني عن استشارة
          أخصائي تخاطب مؤهل.
        </div>

        {startAssessment.isError && (
          <p role="alert" className="text-sm text-danger-600">
            {getArabicErrorMessage(startAssessment.error, "assessment-age")}
          </p>
        )}

        <Button size="lg" isLoading={startAssessment.isPending} onClick={handleStart}>
          {inProgress ? "متابعة التقييم الحالي" : "ابدأ التقييم"}
        </Button>
      </Card>
    </div>
  );
}
