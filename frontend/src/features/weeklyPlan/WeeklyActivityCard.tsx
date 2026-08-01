import { useState } from "react";

import { ActivityExplanationCard } from "@/components/ActivityExplanationCard";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { useActivityExplanation } from "@/features/ai/useAiAssistance";
import type { WeeklyPlanActivityResponse } from "@/types/api";

interface WeeklyActivityCardProps {
  slot: WeeklyPlanActivityResponse;
  isUpdating: boolean;
  allowAlternative?: boolean;
  onToggleCompleted: () => void;
  onRequestAlternative: () => void;
}

export function WeeklyActivityCard({
  slot,
  isUpdating,
  allowAlternative = true,
  onToggleCompleted,
  onRequestAlternative,
}: WeeklyActivityCardProps) {
  const { activity } = slot;
  const [explanationRequested, setExplanationRequested] = useState(false);
  const explanationQuery = useActivityExplanation(slot.id, explanationRequested);

  return (
    <Card className={slot.completed ? "border-2 border-success-500 bg-success-50" : ""}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs text-primary-500">{activity.domain}</p>
          <h3 className="font-semibold text-primary-900">{activity.name}</h3>
        </div>
        {slot.completed && <span className="text-sm font-medium text-success-600">مكتمل ✓</span>}
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-sm text-gray-700">
        <div>
          <dt className="text-xs text-gray-500">الهدف</dt>
          <dd>{activity.goal}</dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500">المدة</dt>
          <dd>{activity.duration}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-xs text-gray-500">خطوات التنفيذ</dt>
          <dd>{activity.description}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-xs text-gray-500">الأدوات</dt>
          <dd>{activity.tools}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-xs text-gray-500">تعليمات لولي الأمر</dt>
          <dd>{activity.parent_instructions}</dd>
        </div>
      </dl>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={slot.completed ? "outline" : "primary"}
          isLoading={isUpdating}
          onClick={onToggleCompleted}
          title={slot.completed ? "اضغط لإلغاء الإنجاز" : "تأكيد إنجاز النشاط"}
        >
          {slot.completed ? "مكتمل" : "تم"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          isLoading={isUpdating}
          disabled={!allowAlternative}
          title={
            allowAlternative
              ? "طلب نشاط آخر معتمد"
              : "لا يمكن تغيير الأنشطة بعد بدء إعادة التقييم"
          }
          onClick={onRequestAlternative}
        >
          طلب نشاط بديل
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={explanationRequested && explanationQuery.isFetching}
          onClick={() => setExplanationRequested(true)}
        >
          افهم أكثر
        </Button>
      </div>

      {explanationRequested && (
        <ActivityExplanationCard
          data={explanationQuery.data}
          isPending={explanationQuery.isPending}
          isError={explanationQuery.isError}
          isFetching={explanationQuery.isFetching}
          onRetry={() => {
            if (!explanationQuery.isFetching) {
              void explanationQuery.refetch({ cancelRefetch: false });
            }
          }}
        />
      )}
    </Card>
  );
}
