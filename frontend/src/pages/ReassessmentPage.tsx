import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "@/api/ApiError";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { SkeletonCard } from "@/components/Skeleton";
import { useAssessmentsForChild, useStartAssessment } from "@/features/assessment/useAssessments";
import { useChild } from "@/features/children/useChildren";
import { useActiveWeeklyPlan } from "@/features/weeklyPlan/useWeeklyPlan";
import { getArabicErrorMessage } from "@/utils/errorMessages";
import { formatArabicDate, formatArabicPercent } from "@/utils/formatArabic";

export function ReassessmentPage() {
  const { childId } = useParams<{ childId: string }>();
  const navigate = useNavigate();
  const childQuery = useChild(childId);
  const assessmentsQuery = useAssessmentsForChild(childId);
  const activePlanQuery = useActiveWeeklyPlan(childId);
  const startAssessment = useStartAssessment();

  if (childQuery.isPending || assessmentsQuery.isPending || activePlanQuery.isPending) {
    return <SkeletonCard />;
  }
  if (childQuery.isError) {
    return (
      <ErrorState
        message={getArabicErrorMessage(childQuery.error)}
        onRetry={() => void childQuery.refetch()}
      />
    );
  }
  if (assessmentsQuery.isError) {
    return (
      <ErrorState
        message={getArabicErrorMessage(assessmentsQuery.error)}
        onRetry={() => void assessmentsQuery.refetch()}
      />
    );
  }

  const completedAssessments = (assessmentsQuery.data ?? []).filter(
    (a) => a.status === "completed",
  );
  const latestCompletedAssessment = completedAssessments[0];
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

  const noActivePlan =
    activePlanQuery.error instanceof ApiError && activePlanQuery.error.status === 404;
  if (noActivePlan) {
    return (
      <EmptyState
        title="لا توجد خطة أسبوعية نشطة للمتابعة"
        description="أنشئ الخطة الأسبوعية من نتيجة آخر تقييم قبل بدء المتابعة الأسبوعية."
        action={
          latestCompletedAssessment && (
            <Link to={`/assessments/${latestCompletedAssessment.id}/result`}>
              <Button>العودة إلى نتيجة التقييم</Button>
            </Link>
          )
        }
      />
    );
  }
  if (activePlanQuery.isError) {
    return (
      <ErrorState
        message={getArabicErrorMessage(activePlanQuery.error)}
        onRetry={() => void activePlanQuery.refetch()}
      />
    );
  }

  const child = childQuery.data;
  const activePlan = activePlanQuery.data;
  if (!child || !activePlan || !latestCompletedAssessment) return null;

  if (activePlan.assessment_id !== latestCompletedAssessment.id) {
    return (
      <EmptyState
        title="الخطة الأسبوعية لا تطابق آخر تقييم"
        description="أنشئ خطة من نتيجة آخر تقييم مكتمل قبل بدء المتابعة الأسبوعية."
        action={
          <Link to={`/assessments/${latestCompletedAssessment.id}/result`}>
            <Button>العودة إلى نتيجة التقييم</Button>
          </Link>
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
      <h1 className="mb-6 text-2xl font-bold text-primary-900">المتابعة الأسبوعية</h1>
      <div
        data-testid="active-weekly-plan-context"
        data-child-id={child.id}
        data-plan-id={activePlan.id}
        data-assessment-id={activePlan.assessment_id}
      >
        <Card className="mb-4 flex flex-col gap-2">
          <h2 className="font-semibold text-primary-900">بيانات المتابعة</h2>
          <p className="text-sm text-gray-700">الطفل: {child.name}</p>
          <p className="text-sm text-gray-700">
            الخطة النشطة منذ: {formatArabicDate(activePlan.generated_at)}
          </p>
          <p className="text-sm text-gray-700">
            إنجاز الخطة: {activePlan.completed_count} من {activePlan.total_activities} (
            {formatArabicPercent(activePlan.adherence_percent)})
          </p>
        </Card>
      </div>
      <Card className="flex flex-col gap-4">
        <p className="text-gray-700">
          أجب عن أسئلة المتابعة المعتمدة لمقارنة النتائج بآخر تقييم مكتمل، ومتابعة تقدّم الطفل،
          وتحديث الخطة الأسبوعية تلقائيًا.
        </p>
        {startAssessment.isError && (
          <p role="alert" className="text-sm text-danger-600">
            {getArabicErrorMessage(startAssessment.error, "assessment-age")}
          </p>
        )}
        <Button size="lg" isLoading={startAssessment.isPending} onClick={handleStart}>
          {inProgress ? "متابعة أسئلة المتابعة الحالية" : "ابدأ أسئلة المتابعة الأسبوعية"}
        </Button>
      </Card>
    </div>
  );
}
