import { useParams } from "react-router-dom";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { ProgressBar } from "@/components/ProgressBar";
import { SkeletonCard } from "@/components/Skeleton";
import { useToast } from "@/components/ToastContext";
import {
  useActiveWeeklyPlan,
  useRequestAlternativeActivity,
  useSetActivityCompletion,
} from "@/features/weeklyPlan/useWeeklyPlan";
import { WeeklyActivityCard } from "@/features/weeklyPlan/WeeklyActivityCard";
import { ApiError } from "@/api/ApiError";
import { getArabicErrorMessage } from "@/utils/errorMessages";
import { dayIndex } from "@/utils/weekDays";

export function WeeklyPlanPage() {
  const { childId } = useParams<{ childId: string }>();
  const { showToast } = useToast();
  const planQuery = useActiveWeeklyPlan(childId);
  const setCompletion = useSetActivityCompletion(childId ?? "");
  const requestAlternative = useRequestAlternativeActivity(childId ?? "");

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
    setCompletion.mutate(
      { activitySlotId, completed: !completed },
      { onError: (error) => showToast(getArabicErrorMessage(error), "error") },
    );
  }

  function handleAlternative(activitySlotId: string): void {
    requestAlternative.mutate(activitySlotId, {
      onSuccess: () => showToast("تم استبدال النشاط بنشاط بديل.", "success"),
      onError: (error) => showToast(getArabicErrorMessage(error), "error"),
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
                    isUpdating={setCompletion.isPending || requestAlternative.isPending}
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
