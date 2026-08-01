import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Skeleton } from "@/components/Skeleton";
import { SourceReferenceDisclosure } from "@/components/SourceReferenceDisclosure";
import type { ActivityExplanationResponse, AIFallbackReason } from "@/types/api";

const RETRYABLE_FALLBACKS: ReadonlySet<AIFallbackReason> = new Set([
  "timeout",
  "provider_timeout",
  "rate_limited",
  "provider_unavailable",
  "provider_error",
  "invalid_output",
  "unsafe_output",
  "ungrounded_output",
]);

interface ActivityExplanationCardProps {
  data: ActivityExplanationResponse | undefined;
  isPending: boolean;
  isError: boolean;
  isFetching?: boolean;
  onRetry: () => void;
}

/** Renders the "افهم أكثر" AI-assisted explanation for one weekly activity. */
export function ActivityExplanationCard({
  data,
  isPending,
  isError,
  isFetching = false,
  onRetry,
}: ActivityExplanationCardProps) {
  if (isPending || isFetching) {
    return (
      <Card dir="rtl" className="mt-3">
        <div role="status" className="flex flex-col gap-2">
          <span className="text-sm text-gray-600">جارٍ إعداد شرح مبسّط للنشاط…</span>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-4/5" />
        </div>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card dir="rtl" className="mt-3">
        <p role="alert" className="text-sm text-gray-700">
          تعذر تحميل الشرح الآن. جرّبوا مرة أخرى، أو استخدموا إرشادات النشاط أعلاه.
        </p>
        <Button className="mt-3" size="sm" variant="outline" onClick={onRetry}>
          إعادة المحاولة
        </Button>
      </Card>
    );
  }

  const { content } = data;
  const isGemini = data.generation_source === "gemini";
  const retryable =
    data.fallback_reason !== null && RETRYABLE_FALLBACKS.has(data.fallback_reason);

  return (
    <Card dir="rtl" className="mt-3 border border-secondary-300 bg-secondary-50/40">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="font-semibold text-primary-900">افهم أكثر: {content.title_ar}</h3>
        <span className="rounded-full bg-white px-3 py-1 text-xs text-primary-700 ring-1 ring-primary-100">
          {isGemini ? "شرح بالذكاء الاصطناعي" : "شرح آمن من النظام"}
        </span>
      </div>

      <p className="mt-3 text-sm leading-7 text-gray-800">{content.simple_explanation_ar}</p>

      <div className="mt-3">
        <h4 className="text-sm font-semibold text-primary-900">الهدف</h4>
        <p className="mt-1 text-sm text-gray-700">{content.purpose_ar}</p>
      </div>

      <div className="mt-3">
        <h4 className="text-sm font-semibold text-primary-900">خطوات التنفيذ</h4>
        <ol className="mt-1 flex flex-col gap-1 text-sm text-gray-700">
          {content.steps_ar.map((step, index) => (
            <li key={index}>
              {index + 1}. {step}
            </li>
          ))}
        </ol>
      </div>

      <div className="mt-3 rounded-lg bg-white p-3 ring-1 ring-primary-100">
        <h4 className="text-sm font-semibold text-primary-900">مثال حوار</h4>
        <p className="mt-1 text-sm text-gray-700">
          <span className="font-medium">ولي الأمر:</span> {content.example_dialogue.parent_text}
        </p>
        <p className="mt-1 text-sm text-gray-700">
          <span className="font-medium">مثال محتمل لاستجابة الطفل:</span>{" "}
          {content.example_dialogue.example_child_response}
        </p>
        <p className="mt-1 text-sm text-gray-700">
          <span className="font-medium">متابعة داعمة:</span>{" "}
          {content.example_dialogue.supportive_parent_continuation}
        </p>
      </div>

      <div className="mt-3">
        <h4 className="text-sm font-semibold text-primary-900">إذا لم يستجب الطفل</h4>
        <p className="mt-1 text-sm text-gray-700">{content.alternative_ar}</p>
      </div>

      <SourceReferenceDisclosure
        sourceIds={content.source_ids}
        sourceReferences={data.source_references}
      />
      {retryable && (
        <Button className="mt-3" size="sm" variant="outline" onClick={onRetry}>
          إعادة المحاولة بالذكاء الاصطناعي
        </Button>
      )}
    </Card>
  );
}
