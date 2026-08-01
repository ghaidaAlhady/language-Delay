import { useRef } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "@/api/ApiError";
import { AiAssistanceCard } from "@/components/AiAssistanceCard";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { ProgressBar } from "@/components/ProgressBar";
import { SkeletonCard } from "@/components/Skeleton";
import { useToast } from "@/components/ToastContext";
import { useWeeklyPlanAssistance } from "@/features/ai/useAiAssistance";
import { activitiesRemainingForEligibility, isReassessmentEligible } from "@/features/weeklyPlan/eligibility";
import {
  useActiveWeeklyPlan,
  useRequestAlternativeActivity,
  useSetActivityCompletion,
} from "@/features/weeklyPlan/useWeeklyPlan";
import { WeeklyActivityCard } from "@/features/weeklyPlan/WeeklyActivityCard";
import { getArabicErrorMessage } from "@/utils/errorMessages";
import { dayIndex } from "@/utils/weekDays";

export function WeeklyPlanPage() {
  const { childId } = useParams<{ childId: string }>();
  const { showToast } = useToast();
  const planQuery = useActiveWeeklyPlan(childId);
  const assistanceQuery = useWeeklyPlanAssistance(
    planQuery.data?.id,
    Boolean(planQuery.data),
  );
  const setCompletion = useSetActivityCompletion(childId ?? "");
  const requestAlternative = useRequestAlternativeActivity(childId ?? "");
  const completionInFlightRef = useRef(new Set<string>());
  const alternativeInFlightRef = useRef(new Set<string>());

  if (planQuery.isPending) return <SkeletonCard />;

  const notFound = planQuery.error instanceof ApiError && planQuery.error.status === 404;

  if (notFound) {
    return (
      <EmptyState
        title="لا توجد خطة أسبوعية بعد"
        description="أكمل تقييمًا أولاً لإنشاء خطة أنشطة أسبوعية مخصصة."
      />
    );
  }

  if (planQuery.isError) {
    return <ErrorState message={getArabicErrorMessage(planQuery.error)} onRetry={() => void planQuery.refetch()} />;
  }

  const plan = planQuery.data;
  if (!plan) return null;

  const activitiesByDay = new Map<string, typeof plan.activities>();
  for (const activity of plan.activities) {
    const bucket = activitiesByDay.get(activity.day) ?? [];
    bucket.push(activity);
    activitiesByDay.set(activity.day, bucket);
  }
  const days = [...activitiesByDay.keys()].sort((a, b) => dayIndex(a) - dayIndex(b));

  function handleToggle(activitySlotId: string, completed: boolean): void {
    if (completionInFlightRef.current.has(activitySlotId)) return;
    completionInFlightRef.current.add(activitySlotId);
    setCompletion.mutate(
      { activitySlotId, completed: !completed },
      {
        onError: (error) => showToast(getArabicErrorMessage(error), "error"),
        onSettled: () => completionInFlightRef.current.delete(activitySlotId),
      },
    );
  }

  function handleAlternative(activitySlotId: string): void {
    if (alternativeInFlightRef.current.has(activitySlotId)) return;
    alternativeInFlightRef.current.add(activitySlotId);
    requestAlternative.mutate(activitySlotId, {
      onSuccess: () => showToast("تم استبدال النشاط بنشاط بديل.", "success"),
      onError: (error) => showToast(getArabicErrorMessage(error), "error"),
      onSettled: () => alternativeInFlightRef.current.delete(activitySlotId),
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-primary-900">الخطة الأسبوعية</h1>
        <p className="text-gray-600">يتم تخصيص الأنشطة بناءً على نتائج التقييم.</p>
      </div>

      <Card>
        <ProgressBar
          value={plan.completed_count}
          max={plan.total_activities}
          label={`الإنجاز — ${plan.completed_count} من ${plan.total_activities}`}
        />
      </Card>

      <AiAssistanceCard
        heading="ملخص الخطة الأسبوعية"
        data={assistanceQuery.data}
        isPending={assistanceQuery.isPending}
        isError={assistanceQuery.isError}
        isFetching={assistanceQuery.isFetching}
        onRetry={() => {
          if (!assistanceQuery.isFetching) {
            void assistanceQuery.refetch({ cancelRefetch: false });
          }
        }}
      />

      {plan.is_active && (
        <ReassessmentEligibilityCard plan={plan} />
      )}

      {days.length === 0 && <EmptyState title="لا توجد أنشطة في هذه الخطة." />}

      <div className="flex flex-col gap-6">
        {days.map((day) => (
          <section key={day}>
            <h2 className="mb-3 text-lg font-semibold text-primary-900">{day}</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {(activitiesByDay.get(day) ?? [])
                .sort((a, b) => a.slot_order - b.slot_order)
                .map((slot) => (
                  <WeeklyActivityCard
                    key={slot.id}
                    slot={slot}
                    allowAlternative={!plan.reassessment_started}
                    isUpdating={
                      (setCompletion.isPending &&
                        setCompletion.variables?.activitySlotId === slot.id) ||
                      (requestAlternative.isPending &&
                        requestAlternative.variables === slot.id)
                    }
                    onToggleCompleted={() => handleToggle(slot.id, slot.completed)}
                    onRequestAlternative={() => handleAlternative(slot.id)}
                  />
                ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

interface ReassessmentEligibilityCardProps {
  plan: {
    id: string;
    child_id: string;
    total_activities: number;
    completed_count: number;
    reassessment_started: boolean;
  };
}

function ReassessmentEligibilityCard({ plan }: ReassessmentEligibilityCardProps) {
  if (plan.total_activities === 0) return null;

  const eligible = isReassessmentEligible(plan.completed_count, plan.total_activities);
  const remaining = activitiesRemainingForEligibility(plan.completed_count, plan.total_activities);
  const hasStartedFollowup = plan.reassessment_started;

  return (
    <Card className={eligible ? "border-2 border-success-500 bg-success-50 text-center" : "text-center"}>
      <h2 className="text-xl font-bold text-primary-900">
        {eligible ? "أصبحت إعادة التقييم متاحة" : "إعادة التقييم الأسبوعي"}
      </h2>
      <p className="mt-2 text-gray-700">
        {eligible
          ? `أكملتِ ${plan.completed_count} من ${plan.total_activities} نشاطًا — أصبحت إعادة التقييم متاحة.`
          : "يمكنك بدء إعادة التقييم بعد إكمال 70% من الأنشطة."}
      </p>
      {!eligible && remaining > 0 && (
        <p className="mt-1 text-sm text-gray-600">
          {remaining === 1
            ? "أكملي نشاطًا واحدًا إضافيًا لفتح إعادة التقييم."
            : `أكملي ${remaining} أنشطة إضافية لفتح إعادة التقييم.`}
        </p>
      )}
      <div className="mt-4">
        {eligible ? (
          <Link to={`/children/${plan.child_id}/reassessment?planId=${encodeURIComponent(plan.id)}`}>
            <Button size="lg">
              {hasStartedFollowup ? "متابعة إعادة التقييم" : "بدء إعادة التقييم"}
            </Button>
          </Link>
        ) : (
          <Button size="lg" disabled>
            إعادة التقييم الأسبوعي
          </Button>
        )}
      </div>
    </Card>
  );
}
