import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { ErrorState } from "@/components/ErrorState";
import { ProgressBar } from "@/components/ProgressBar";
import { SkeletonCard } from "@/components/Skeleton";
import {
  useAssessment,
  useAssessmentQuestions,
  useCompleteAssessment,
  useSubmitAnswers,
} from "@/features/assessment/useAssessments";
import { buildAnswerPayload, resumeIndex } from "@/features/assessment/answerMapping";
import { ResponseScale } from "@/features/assessment/ResponseScale";
import type { ResponseValue } from "@/types/api";
import { getArabicErrorMessage, getMissingQuestionCount } from "@/utils/errorMessages";

export function AssessmentTakePage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const navigate = useNavigate();

  const assessmentQuery = useAssessment(assessmentId);
  const questionsQuery = useAssessmentQuestions(assessmentId);
  const submitAnswers = useSubmitAnswers(assessmentId ?? "");
  const completeAssessment = useCompleteAssessment(assessmentId ?? "");

  const [currentIndex, setCurrentIndex] = useState<number | null>(null);
  const [selected, setSelected] = useState<ResponseValue | null>(null);
  // `submitAnswers.isPending` turns false as soon as that mutation settles,
  // but on the last question `completeAssessment.mutate` is only called
  // from *inside* its onSuccess callback — leaving a brief gap where neither
  // mutation reports pending yet, so `isBusy` below would flicker to false
  // and momentarily re-enable the just-answered (still-checked) options.
  // This flag stays true across that gap so the scale never re-opens.
  const [isSubmitting, setIsSubmitting] = useState(false);
  // `isSubmitting` (state) only disables the *rendered* controls, and that
  // disabling only takes effect once React commits the next render — it
  // cannot stop a second `handleNext()` invocation that happens before that
  // commit lands (e.g. a duplicate click event fired in the same tick).
  // A ref is read and written synchronously, independent of the render
  // cycle, so it closes that gap: it's the single source of truth for
  // "a submission is in flight" and is checked before anything else runs.
  const submissionInFlightRef = useRef(false);

  const assessment = assessmentQuery.data;
  const questions = questionsQuery.data;

  // Resume position: the backend doesn't expose *which* question IDs were
  // already answered, only the count. This UI always submits answers in the
  // questions' sorted-ID order, so `answered_count` is a reliable resume
  // index as long as the assessment was only ever answered through this UI.
  useEffect(() => {
    if (currentIndex === null && assessment && questions) {
      setCurrentIndex(resumeIndex(assessment.answered_count, questions.length));
    }
  }, [assessment, questions, currentIndex]);

  useEffect(() => {
    if (assessment?.status === "completed") {
      navigate(`/assessments/${assessment.id}/result`, { replace: true });
    }
  }, [assessment, navigate]);

  if (assessmentQuery.isPending || questionsQuery.isPending || currentIndex === null) {
    return <SkeletonCard />;
  }

  if (assessmentQuery.isError || questionsQuery.isError) {
    return (
      <ErrorState
        message={getArabicErrorMessage(assessmentQuery.error ?? questionsQuery.error)}
        onRetry={() => {
          void assessmentQuery.refetch();
          void questionsQuery.refetch();
        }}
      />
    );
  }

  if (!questions || questions.length === 0 || !assessment) {
    return <ErrorState message="تعذر تحميل أسئلة التقييم." />;
  }

  const currentQuestion = questions[currentIndex];
  if (!currentQuestion) {
    return <ErrorState message="تعذر تحميل أسئلة التقييم." />;
  }
  const isLastQuestion = currentIndex === questions.length - 1;

  function handleNext(): void {
    if (!selected) return;
    if (submissionInFlightRef.current) return;
    submissionInFlightRef.current = true;
    setIsSubmitting(true);
    submitAnswers.mutate(
      buildAnswerPayload(currentQuestion!.id, selected),
      {
        onSuccess: () => {
          if (isLastQuestion) {
            completeAssessment.mutate(undefined, {
              onSuccess: (result) => navigate(`/assessments/${result.id}/result`, { replace: true }),
              onSettled: () => {
                submissionInFlightRef.current = false;
                setIsSubmitting(false);
              },
            });
          } else {
            submissionInFlightRef.current = false;
            setCurrentIndex((index) => (index ?? 0) + 1);
            setSelected(null);
            setIsSubmitting(false);
          }
        },
        onError: () => {
          submissionInFlightRef.current = false;
          setIsSubmitting(false);
        },
      },
    );
  }

  function handlePrevious(): void {
    setSelected(null);
    setCurrentIndex((index) => Math.max(0, (index ?? 0) - 1));
  }

  const isBusy = isSubmitting || submitAnswers.isPending || completeAssessment.isPending;
  const missingCount = getMissingQuestionCount(completeAssessment.error);

  return (
    <div className="mx-auto max-w-xl">
      <ProgressBar value={currentIndex} max={questions.length} label={`السؤال ${currentIndex + 1} من ${questions.length}`} />

      <Card className="mt-6 flex flex-col gap-6">
        <div>
          <p className="text-sm font-medium text-primary-500">{currentQuestion.domain}</p>
          <h2 className="mt-1 text-lg font-semibold text-primary-900">{currentQuestion.question}</h2>
        </div>

        <ResponseScale value={selected} onChange={setSelected} disabled={isBusy} />

        {(submitAnswers.isError || completeAssessment.isError) && (
          <p role="alert" className="text-sm text-danger-600">
            {missingCount
              ? `يجب الإجابة عن ${missingCount} سؤالًا إضافيًا قبل إنهاء التقييم.`
              : getArabicErrorMessage(submitAnswers.error ?? completeAssessment.error, "assessment-complete")}
          </p>
        )}

        <div className="flex justify-between gap-3">
          <Button type="button" variant="ghost" disabled={currentIndex === 0 || isBusy} onClick={handlePrevious}>
            السابق
          </Button>
          <Button type="button" isLoading={isBusy} disabled={!selected} onClick={handleNext}>
            {isLastQuestion ? "عرض النتائج" : "التالي"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
