import { Link, useParams } from "react-router-dom";

import { AiAssistanceCard } from "@/components/AiAssistanceCard";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { ErrorState } from "@/components/ErrorState";
import { SkeletonCard } from "@/components/Skeleton";
import { useFollowupAssistance } from "@/features/ai/useAiAssistance";
import { useFollowup } from "@/features/followup/useFollowups";
import { getArabicErrorMessage } from "@/utils/errorMessages";
import { formatArabicDate, formatArabicPercent } from "@/utils/formatArabic";

export function FollowupDetailPage() {
  const { followupId } = useParams<{ followupId: string }>();
  const followupQuery = useFollowup(followupId);
  const assistanceQuery = useFollowupAssistance(
    followupId,
    Boolean(followupQuery.data),
  );

  if (followupQuery.isPending) return <SkeletonCard />;
  if (followupQuery.isError) {
    return <ErrorState message={getArabicErrorMessage(followupQuery.error)} onRetry={() => void followupQuery.refetch()} />;
  }

  const followup = followupQuery.data;
  if (!followup) return null;

  const improved = followup.improvement_percent > 0;
  const isWeeklyPlanProgress = followup.weekly_plan_id !== null;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div>
        <p className="text-sm text-gray-500">{formatArabicDate(followup.created_at)}</p>
        <h1 className="text-2xl font-bold text-primary-900">نتيجة المتابعة الأسبوعية</h1>
      </div>

      <Card className="grid grid-cols-2 gap-4 text-center sm:grid-cols-3">
        <Stat
          label={isWeeklyPlanProgress ? "إنجاز أنشطة الخطة" : "النتيجة السابقة"}
          value={formatArabicPercent(followup.previous_score_percent)}
        />
        <Stat
          label={isWeeklyPlanProgress ? "تحقق المهارات المستهدفة" : "النتيجة الحالية"}
          value={formatArabicPercent(followup.current_score_percent)}
        />
        <Stat
          label={isWeeklyPlanProgress ? "مؤشر التقدم الأسبوعي" : "نسبة التحسن"}
          value={`${!isWeeklyPlanProgress && followup.improvement_percent > 0 ? "+" : ""}${formatArabicPercent(followup.improvement_percent)}`}
          highlight={improved}
        />
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <h2 className="mb-2 font-semibold text-success-600">المجالات المتحسنة</h2>
          {followup.improved_domains.length === 0 ? (
            <p className="text-sm text-gray-500">لا يوجد تحسن ملحوظ بعد.</p>
          ) : (
            <ul className="flex flex-col gap-1 text-sm text-gray-700">
              {followup.improved_domains.map((d) => (
                <li key={d}>• {d}</li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <h2 className="mb-2 font-semibold text-warning-600">مجالات تحتاج دعمًا</h2>
          {followup.support_needed_domains.length === 0 ? (
            <p className="text-sm text-gray-500">لا يوجد.</p>
          ) : (
            <ul className="flex flex-col gap-1 text-sm text-gray-700">
              {followup.support_needed_domains.map((d) => (
                <li key={d}>• {d}</li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card>
        <h2 className="mb-1 font-semibold text-primary-900">تعليق</h2>
        <p className="text-sm text-gray-700">{followup.comment}</p>
        <p className="mt-3 text-sm text-gray-600">الهدف القادم: {followup.next_goal}</p>
      </Card>

      <AiAssistanceCard
        heading="ملخص تقدم الأسبوع"
        data={assistanceQuery.data}
        isPending={assistanceQuery.isPending}
        isError={assistanceQuery.isError}
        onRetry={() => void assistanceQuery.refetch()}
      />

      <div className="flex justify-center">
        <Link to={`/children/${followup.child_id}/weekly-plan`}>
          <Button>عرض الخطة الأسبوعية المحدّثة</Button>
        </Link>
      </div>
    </div>
  );
}

function Stat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div>
      <p className={`text-lg font-bold ${highlight ? "text-success-600" : "text-primary-900"}`}>{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  );
}
