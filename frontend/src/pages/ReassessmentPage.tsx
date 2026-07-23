import { Link, useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { SkeletonCard } from "@/components/Skeleton";
import { useAssessmentsForChild, useStartAssessment } from "@/features/assessment/useAssessments";
import { getArabicErrorMessage } from "@/utils/errorMessages";

export function ReassessmentPage() {
  const { childId } = useParams<{ childId: string }>();
  const navigate = useNavigate();
  const assessmentsQuery = useAssessmentsForChild(childId);
  const startAssessment = useStartAssessment();

  if (assessmentsQuery.isPending) return <SkeletonCard />;
  if (assessmentsQuery.isError) {
    return (
      <ErrorState
        message={getArabicErrorMessage(assessmentsQuery.error)}
        onRetry={() => void assessmentsQuery.refetch()}
      />
    );
  }

  const completedAssessments = (assessmentsQuery.data ?? []).filter((a) => a.status === "completed");
  const inProgress = (assessmentsQuery.data ?? []).find((a) => a.status === "in_progress");

  if (completedAssessments.length === 0) {
    return (
      <EmptyState
        title="لا توجد تقييمات سابقة"
        description="يلزم إجراء تقييمين على الأقل للمقارنة."
        action={
          childId && (
            <Link to={`/children/${childId}/assessment/intro`}>
              <Button>ابدأ التقييم الأول</Button>
            </Link>
          )
        }
      />
    );
  }

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

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-6 text-2xl font-bold text-primary-900">إعادة التقييم</h1>
      <Card className="flex flex-col gap-4">
        <p className="text-gray-700">
          سيتم إجراء تقييم جديد لمقارنة النتائج بآخر تقييم مكتمل، ومتابعة تقدّم الطفل، وتحديث
          الخطة الأسبوعية تلقائيًا.
        </p>
        {startAssessment.isError && (
          <p role="alert" className="text-sm text-danger-600">
            {getArabicErrorMessage(startAssessment.error, "assessment-age")}
          </p>
        )}
        <Button size="lg" isLoading={startAssessment.isPending} onClick={handleStart}>
          {inProgress ? "متابعة التقييم الحالي" : "ابدأ إعادة التقييم"}
        </Button>
      </Card>
    </div>
  );
}
