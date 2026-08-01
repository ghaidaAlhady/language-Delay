import type { AISourceReference } from "@/types/api";

const NEUTRAL_LABEL = "مصدر معتمد";

interface SourceReferenceDisclosureProps {
  sourceIds: string[];
  sourceReferences: AISourceReference[];
}

/**
 * Compact, accessible, collapsed-by-default disclosure for AI-card source
 * traceability — replaces rendering raw comma-separated source IDs as
 * primary card content. Human-readable labels come only from
 * `sourceReferences` (server-resolved from the approved knowledge base,
 * never from provider output); the raw ID stays available as small,
 * secondary text for traceability.
 */
export function SourceReferenceDisclosure({
  sourceIds,
  sourceReferences,
}: SourceReferenceDisclosureProps) {
  if (sourceIds.length === 0) return null;

  const referenceById = new Map(sourceReferences.map((reference) => [reference.source_id, reference]));

  return (
    <details className="mt-3 text-sm text-gray-700">
      <summary className="cursor-pointer select-none text-xs font-medium text-gray-500 hover:text-primary-700">
        المصادر المعتمدة ({sourceIds.length})
      </summary>
      <ul className="mt-2 flex flex-col gap-1.5 ps-1">
        {sourceIds.map((sourceId) => {
          const reference = referenceById.get(sourceId);
          return (
            <li key={sourceId} className="flex flex-col rounded-lg bg-gray-50 px-2.5 py-1.5">
              <span className="text-sm text-primary-900">{reference?.label_ar ?? NEUTRAL_LABEL}</span>
              <span className="text-xs text-gray-500" title={sourceId}>
                {sourceId}
              </span>
            </li>
          );
        })}
      </ul>
    </details>
  );
}
