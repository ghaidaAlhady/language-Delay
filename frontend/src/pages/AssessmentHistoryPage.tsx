import { Link, useParams } from "react-router-dom";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { SeverityBadge } from "@/components/SeverityBadge";
import { SkeletonCard } from "@/components/Skeleton";
import { useAssessmentsForChild } from "@/features/assessment/useAssessments";
import { getArabicErrorMessage } from "@/utils/errorMessages";
import { formatArabicDate } from "@/utils/formatArabic";

export function AssessmentHistoryPage() {
  const { childId } = useParams<{ childId: string }>();
  const assessmentsQuery = useAssessmentsForChild(childId);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-primary-900">سجل التقييمات</h1>

      {assessmentsQuery.isPending && <SkeletonCard />}
      {assessmentsQuery.isError && (
        <ErrorState
          message={getArabicErrorMessage(assessmentsQuery.error)}
          onRetry={() => void assessmentsQuery.refetch()}
        />
      )}
      {assessmentsQuery.data && assessmentsQuery.data.length === 0 && (
        <EmptyState title="لا توجد تقييمات بعد" />
      )}

      <div className="flex flex-col gap-3">
        {assessmentsQuery.data?.map((assessment) => {
          const content = (
            <Card className="flex flex-wrap items-center justify-between gap-3 transition-shadow hover:shadow-md">
              <div>
                <p className="text-sm text-gray-500">{formatArabicDate(assessment.started_at)}</p>
                <p className="font-medium text-primary-900">
                  {assessment.status === "completed" ? "مكتمل" : "قيد التنفيذ"} — العمر عند
                  التقييم: {assessment.age_at_assessment}
                </p>
              </div>
              {assessment.overall_severity && <SeverityBadge severity={assessment.overall_severity} />}
            </Card>
          );
          return (
            <Link
              key={assessment.id}
              to={
                assessment.status === "completed"
                  ? `/assessments/${assessment.id}/result`
                  : `/assessments/${assessment.id}/take`
              }
            >
              {content}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
