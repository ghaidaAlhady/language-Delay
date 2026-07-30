import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Skeleton } from "@/components/Skeleton";
import type { AIAssistanceResponse, AIFallbackReason } from "@/types/api";

const RETRYABLE_FALLBACKS: ReadonlySet<AIFallbackReason> = new Set([
  "timeout",
  "provider_error",
  "invalid_output",
  "unsafe_output",
  "ungrounded_output",
]);

interface AiAssistanceCardProps {
  heading: string;
  data: AIAssistanceResponse | undefined;
  isPending: boolean;
  isError: boolean;
  onRetry: () => void;
}

export function AiAssistanceCard({
  heading,
  data,
  isPending,
  isError,
  onRetry,
}: AiAssistanceCardProps) {
  if (isPending) {
    return (
      <Card aria-label={heading} dir="rtl">
        <h2 className="font-semibold text-primary-900">{heading}</h2>
        <div role="status" className="mt-3 flex flex-col gap-2">
          <span className="text-sm text-gray-600">جارٍ إعداد الصياغة المساندة…</span>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-4/5" />
        </div>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card aria-label={heading} dir="rtl">
        <h2 className="font-semibold text-primary-900">{heading}</h2>
        <p role="alert" className="mt-2 text-sm text-gray-700">
          تعذر تحميل الصياغة المساندة. تظل النتيجة الحتمية أعلاه هي المرجع.
        </p>
        <Button className="mt-3" size="sm" variant="outline" onClick={onRetry}>
          إعادة المحاولة
        </Button>
      </Card>
    );
  }

  const isGemini = data.generation_source === "gemini";
  const retryable = data.fallback_reason !== null && RETRYABLE_FALLBACKS.has(data.fallback_reason);

  return (
    <Card aria-label={heading} dir="rtl" className="border border-secondary-300 bg-secondary-50/40">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h2 className="font-semibold text-primary-900">{heading}</h2>
        <span className="rounded-full bg-white px-3 py-1 text-xs text-primary-700 ring-1 ring-primary-100">
          {isGemini ? "صياغة مساندة بالذكاء الاصطناعي" : "ملخص آمن من النظام"}
        </span>
      </div>
      {!isGemini && (
        <p className="mt-2 text-xs text-gray-600">
          لم تتوفر صياغة الذكاء الاصطناعي، لذا نعرض ملخصاً حتمياً آمناً.
        </p>
      )}
      <p className="mt-3 text-sm leading-7 text-gray-800">{data.content.summary}</p>
      <p className="mt-2 text-sm font-medium text-primary-800">{data.content.encouragement}</p>
      {data.content.action_tips.length > 0 && (
        <ul className="mt-3 flex flex-col gap-2 text-sm text-gray-700">
          {data.content.action_tips.map((tip) => (
            <li key={`${tip.source_id}-${tip.text}`}>
              • {tip.text}
              <span className="ms-1 text-xs text-gray-500">({tip.source_id})</span>
            </li>
          ))}
        </ul>
      )}
      {data.content.source_ids.length > 0 && (
        <p className="mt-3 text-xs text-gray-500">
          المصادر المعتمدة: {data.content.source_ids.join("، ")}
        </p>
      )}
      <p className="mt-4 border-t border-primary-100 pt-3 text-xs leading-6 text-gray-600">
        {data.content.disclaimer}
      </p>
      {retryable && (
        <Button className="mt-3" size="sm" variant="outline" onClick={onRetry}>
          إعادة المحاولة
        </Button>
      )}
    </Card>
  );
}
