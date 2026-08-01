"""Human-readable source labels, resolved only from the approved KB context.

Never provider-supplied: `build_source_references` reads exclusively from the
`GroundingRecord`s the backend already assembled (`title`/`source_type`),
after the provider's output has been validated — Gemini has no way to invent
or override a label.
"""
from __future__ import annotations

from app.ai.schemas import GroundingRecord, SourceReference

_NEUTRAL_LABEL = "مصدر معتمد"

_CATEGORY_LABELS: dict[str, str] = {
    "KB02_activity": "نشاط معتمد",
    "KB03_decision_rule": "قاعدة قرار معتمدة",
    "KB06_followup_question": "سؤال متابعة معتمد",
    "KB06_followup_candidate": "سؤال متابعة معتمد",
}


def build_source_references(
    source_ids: list[str], approved_sources: list[GroundingRecord]
) -> list[SourceReference]:
    by_id = {source.source_id: source for source in approved_sources}
    references: list[SourceReference] = []
    for source_id in source_ids:
        source = by_id.get(source_id)
        if source is None:
            references.append(
                SourceReference(
                    source_id=source_id, label_ar=_NEUTRAL_LABEL, category=_NEUTRAL_LABEL
                )
            )
            continue
        references.append(
            SourceReference(
                source_id=source_id,
                label_ar=source.title,
                category=_CATEGORY_LABELS.get(source.source_type, _NEUTRAL_LABEL),
            )
        )
    return references
