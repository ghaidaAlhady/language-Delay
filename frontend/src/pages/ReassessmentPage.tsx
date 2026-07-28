import { useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { ApiError } from "@/api/ApiError";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { SkeletonCard } from "@/components/Skeleton";
import { ResponseScale } from "@/features/assessment/ResponseScale";
import { useChild } from "@/features/children/useChildren";
import {
  useSubmitWeeklyFollowup,
  useWeeklyFollowupQuestions,
} from "@/features/followup/useFollowups";
import { useActiveWeeklyPlan } from "@/features/weeklyPlan/useWeeklyPlan";
import type { ResponseValue } from "@/types/api";
import { getArabicErrorMessage } from "@/utils/errorMessages";
import { formatArabicDate } from "@/utils/formatArabic";

export function ReassessmentPage() {
  const { childId } = useParams<{ childId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const requestedPlanId = searchParams.get("planId");
  const childQuery = useChild(childId);
  const activePlanQuery = useActiveWeeklyPlan(childId);
  const activePlan = activePlanQuery.data;
  const planMatchesRequest = !requestedPlanId || requestedPlanId === activePlan?.id;
  const planIsComplete =
    Boolean(activePlan?.is_active) &&
    (activePlan?.total_activities ?? 0) > 0 &&
    activePlan?.completed_count === activePlan?.total_activities;
  const readyPlanId =
    planMatchesRequest && planIsComplete ? activePlan?.id : undefined;
  const contextQuery = useWeeklyFollowupQuestions(readyPlanId);
  const submitFollowup = useSubmitWeeklyFollowup(
    childId ?? "",
    readyPlanId ?? "",
  );
  const [answers, setAnswers] = useState<Record<string, ResponseValue>>({});
  const submissionInFlightRef = useRef(false);

  if (
    childQuery.isPending ||
    activePlanQuery.isPending ||
    (readyPlanId && contextQuery.isPending)
  ) {
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

  const noActivePlan =
    activePlanQuery.error instanceof ApiError &&
    activePlanQuery.error.status === 404;
  if (noActivePlan) {
    return (
      <EmptyState
        title="لا توجد خطة أسبوعية نشطة للمتابعة"
        description="أنشئ الخطة الأسبوعية من نتيجة التقييم قبل بدء المتابعة الأسبوعية."
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
  if (!activePlan || !childQuery.data) return null;

  if (!planMatchesRequest) {
    return (
      <EmptyState
        title="الخطة المحددة لم تعد نشطة"
        description="تم إنشاء خطة أحدث. افتح الخطة الأسبوعية الحالية للمتابعة."
        action={
          childId && (
            <Link to={`/children/${childId}/weekly-plan`}>
              <Button>عرض الخطة الحالية</Button>
            </Link>
          )
        }
      />
    );
  }

  if (!planIsComplete) {
    return (
      <EmptyState
        title="أكمل الخطة الأسبوعية أولًا"
        description="تظهر المتابعة الأسبوعية بعد إكمال جميع أنشطة الخطة النشطة."
        action={
          childId && (
            <Link to={`/children/${childId}/weekly-plan`}>
              <Button>العودة إلى الخطة الأسبوعية</Button>
            </Link>
          )
        }
      />
    );
  }

  if (contextQuery.isError) {
    return (
      <ErrorState
        message={getArabicErrorMessage(contextQuery.error)}
        onRetry={() => void contextQuery.refetch()}
      />
    );
  }

  const context = contextQuery.data;
  if (
    !context ||
    context.child_id !== childQuery.data.id ||
    context.weekly_plan_id !== activePlan.id ||
    context.questions.length < 5 ||
    context.questions.length > 8
  ) {
    return <ErrorState message="تعذر تحميل أسئلة المتابعة الأسبوعية لهذه الخطة." />;
  }

  const allAnswered = context.questions.every((question) => answers[question.id]);

  function handleSubmit(): void {
    if (!allAnswered || submissionInFlightRef.current) return;
    submissionInFlightRef.current = true;
    submitFollowup.mutate(
      {
        answers: context!.questions.map((question) => ({
          question_id: question.id,
          response: answers[question.id]!,
        })),
      },
      {
        onSuccess: (followup) =>
          navigate(`/followups/${followup.id}`, { replace: true }),
        onSettled: () => {
          submissionInFlightRef.current = false;
        },
      },
    );
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-primary-900">المتابعة الأسبوعية</h1>
        <p className="text-gray-600">
          قيّم المهارات التي تدرب عليها الطفل في الخطة الحالية. هذه متابعة
          للتقدم وليست تشخيصًا طبيًا.
        </p>
      </div>

      <Card
        className="flex flex-col gap-2"
        data-testid="active-weekly-plan-context"
        data-child-id={context.child_id}
        data-plan-id={context.weekly_plan_id}
        data-assessment-id={context.assessment_id}
      >
        <h2 className="font-semibold text-primary-900">بيانات المتابعة</h2>
        <p className="text-sm text-gray-700">الطفل: {context.child_name}</p>
        <p className="text-sm text-gray-700">
          الخطة النشطة منذ: {formatArabicDate(context.generated_at)}
        </p>
        <p className="text-sm text-gray-700">
          إنجاز الخطة: {context.completed_count} من {context.total_activities}
        </p>
        <div className="mt-2">
          <h3 className="text-sm font-semibold text-primary-900">أهداف الخطة الحالية</h3>
          <ul className="mt-1 text-sm text-gray-700">
            {context.weekly_goals.map((goal) => (
              <li key={goal}>• {goal}</li>
            ))}
          </ul>
        </div>
      </Card>

      <div className="flex flex-col gap-4">
        {context.questions.map((question, index) => (
          <Card
            key={question.id}
            data-testid="kb06-weekly-question"
            data-source-file={question.source_file}
            data-activity-id={question.activity_id}
          >
            <p className="text-xs font-medium text-primary-500">
              السؤال {index + 1} من {context.questions.length} • {question.domain}
            </p>
            <h2 className="mb-4 mt-1 font-semibold text-primary-900">
              {question.question}
            </h2>
            <ResponseScale
              value={answers[question.id] ?? null}
              disabled={submitFollowup.isPending}
              onChange={(response) =>
                setAnswers((current) => ({
                  ...current,
                  [question.id]: response,
                }))
              }
            />
          </Card>
        ))}
      </div>

      {submitFollowup.isError && (
        <p role="alert" className="text-sm text-danger-600">
          {getArabicErrorMessage(submitFollowup.error)}
        </p>
      )}

      <div className="flex justify-center">
        <Button
          size="lg"
          disabled={!allAnswered}
          isLoading={submitFollowup.isPending}
          onClick={handleSubmit}
        >
          إرسال المتابعة وإنشاء خطة الأسبوع القادم
        </Button>
      </div>
    </div>
  );
}
