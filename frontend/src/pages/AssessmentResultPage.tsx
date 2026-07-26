import { useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { ErrorState } from "@/components/ErrorState";
import { SeverityBadge } from "@/components/SeverityBadge";
import { SkeletonCard } from "@/components/Skeleton";
import { useAssessment, useAssessmentsForChild } from "@/features/assessment/useAssessments";
import { useCreateFollowup } from "@/features/followup/useFollowups";
import { useGenerateReport } from "@/features/reports/useReports";
import { useGenerateWeeklyPlan } from "@/features/weeklyPlan/useWeeklyPlan";
import { getArabicErrorMessage } from "@/utils/errorMessages";
import { formatArabicPercent } from "@/utils/formatArabic";

export function AssessmentResultPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const navigate = useNavigate();
  const assessmentQuery = useAssessment(assessmentId);
  const childId = assessmentQuery.data?.child_id;
  const siblingAssessmentsQuery = useAssessmentsForChild(childId);
  const generateReport = useGenerateReport();
  const generateWeeklyPlan = useGenerateWeeklyPlan(childId ?? "");
  const createFollowup = useCreateFollowup(childId ?? "");
  const followupSubmissionInFlightRef = useRef(false);

  useEffect(() => {
    if (assessmentQuery.data && assessmentQuery.data.status !== "completed") {
      navigate(`/assessments/${assessmentQuery.data.id}/take`, { replace: true });
    }
  }, [assessmentQuery.data, navigate]);

  if (assessmentQuery.isPending) return <SkeletonCard />;
  if (assessmentQuery.isError) {
    return (
      <ErrorState
        message={getArabicErrorMessage(assessmentQuery.error)}
        onRetry={() => void assessmentQuery.refetch()}
      />
    );
  }

  const assessment = assessmentQuery.data;
  if (!assessment || assessment.status !== "completed") return <SkeletonCard />;

  function handleViewReport(): void {
    generateReport.mutate(assessment!.id, {
      onSuccess: (report) => navigate(`/reports/${report.id}`),
    });
  }

  function handleGeneratePlan(): void {
    generateWeeklyPlan.mutate(assessment!.id, {
      onSuccess: () => navigate(`/children/${assessment!.child_id}/weekly-plan`),
    });
  }

  function handleCompareWithPrevious(): void {
    if (followupSubmissionInFlightRef.current) return;
    followupSubmissionInFlightRef.current = true;
    createFollowup.mutate(assessment!.id, {
      onSuccess: (followup) => navigate(`/followups/${followup.id}`),
      onSettled: () => {
        followupSubmissionInFlightRef.current = false;
      },
    });
  }

  const hasPreviousCompletedAssessment = (siblingAssessmentsQuery.data ?? []).some(
    (a) => a.status === "completed" && a.id !== assessment.id,
  );
  const referralNeeded = assessment.overall_referral !== "لا";

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div className="text-center">
        <p className="text-sm font-medium text-primary-500">نتيجة التقييم الأولي</p>
        <h1 className="mt-1 text-2xl font-bold text-primary-900">النتيجة الكلية</h1>
        {assessment.overall_severity && (
          <div className="mt-3">
            <SeverityBadge severity={assessment.overall_severity} />
          </div>
        )}
        {assessment.confidence_score !== null && (
          <p className="mt-2 text-sm text-gray-500">
            درجة الثقة: {formatArabicPercent(assessment.confidence_score * 100)}
          </p>
        )}
      </div>

      {referralNeeded && (
        <Card className="border-2 border-warning-500 bg-warning-50">
          <h2 className="font-semibold text-primary-900">توصية الإحالة إلى أخصائي</h2>
          <p className="mt-1 text-sm text-gray-700">
            {assessment.overall_referral === "نعم"
              ? "تشير النتائج إلى أهمية مراجعة أخصائي تخاطب لتقييم دقيق."
              : "قد يكون من المفيد النظر في استشارة أخصائي تخاطب، إلى جانب متابعة الأنشطة المنزلية."}
          </p>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <h2 className="mb-2 font-semibold text-success-600">نقاط القوة</h2>
          {assessment.strengths.length === 0 ? (
            <p className="text-sm text-gray-500">لا توجد نقاط قوة بارزة مسجّلة لهذا التقييم.</p>
          ) : (
            <ul className="flex flex-col gap-1 text-sm text-gray-700">
              {assessment.strengths.map((strength) => (
                <li key={strength}>• {strength}</li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <h2 className="mb-2 font-semibold text-warning-600">المهارات التي تحتاج دعمًا</h2>
          {assessment.support_needs.length === 0 ? (
            <p className="text-sm text-gray-500">لا توجد مهارات تحتاج دعمًا إضافيًا حاليًا.</p>
          ) : (
            <ul className="flex flex-col gap-1 text-sm text-gray-700">
              {assessment.support_needs.map((need) => (
                <li key={need}>• {need}</li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card>
        <h2 className="mb-3 font-semibold text-primary-900">مستوى الدعم حسب المجال</h2>
        <div className="flex flex-col gap-4">
          {assessment.domain_results.map((domain) => (
            <div
              key={domain.domain}
              className="border-b border-primary-50 pb-3 last:border-0 last:pb-0"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium text-primary-900">{domain.domain}</p>
                <SeverityBadge severity={domain.severity} />
              </div>
              <p className="mt-1 text-sm text-gray-600">
                النسبة: {formatArabicPercent(domain.score_percent)}
              </p>
              <p className="mt-1 text-sm text-gray-700">{domain.recommendation}</p>
              <p className="mt-1 text-xs text-gray-500">المتابعة: {domain.follow_up}</p>
            </div>
          ))}
        </div>
      </Card>

      {(generateReport.isError || generateWeeklyPlan.isError || createFollowup.isError) && (
        <p role="alert" className="text-center text-sm text-danger-600">
          {getArabicErrorMessage(
            generateReport.error ?? generateWeeklyPlan.error ?? createFollowup.error,
          )}
        </p>
      )}

      <div className="flex flex-wrap justify-center gap-3">
        <Button isLoading={generateReport.isPending} onClick={handleViewReport}>
          عرض التقرير
        </Button>
        <Button
          variant="outline"
          isLoading={generateWeeklyPlan.isPending}
          onClick={handleGeneratePlan}
        >
          إنشاء الخطة الأسبوعية
        </Button>
        {hasPreviousCompletedAssessment && (
          <Button
            variant="secondary"
            isLoading={createFollowup.isPending}
            onClick={handleCompareWithPrevious}
          >
            إكمال المتابعة الأسبوعية
          </Button>
        )}
      </div>
    </div>
  );
}
