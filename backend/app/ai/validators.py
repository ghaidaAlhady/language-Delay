"""Schema, safety, grounding, and immutable-fact validation."""
from __future__ import annotations

import re

from pydantic import ValidationError

from app.ai.schemas import AssistanceContent, AssistanceContext
from app.core.constants import DISCLAIMER_AR
from app.rag.schemas import Severity


class InvalidOutputError(Exception):
    """The provider returned malformed or contract-breaking output."""


class UnsafeOutputError(Exception):
    """The provider returned unsafe or contradictory wording."""


class UngroundedOutputError(Exception):
    """The provider cited or recommended content outside approved KB context."""


_URL_OR_MARKUP = re.compile(r"https?://|www\.|```|<[^>]+>", re.IGNORECASE)
_ACTIVITY_ID = re.compile(r"\bA\d{3,}\b", re.IGNORECASE)
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*[%٪]")
_FORBIDDEN_TERMS = (
    "تشخيص",
    "مرض",
    "دواء",
    "جرعة",
    "علاج",
    "diagnos",
    "disease",
    "medicat",
    "dosage",
    "treatment",
)


def _content_body(content: AssistanceContent) -> str:
    return " ".join(
        [
            content.title,
            content.summary,
            content.encouragement,
            *(tip.text for tip in content.action_tips),
        ]
    )


def _validate_immutable_facts(
    content: AssistanceContent, context: AssistanceContext
) -> None:
    body = _content_body(content)

    expected_severity = context.immutable_facts.get("overall_severity")
    if isinstance(expected_severity, str):
        for severity in Severity:
            if severity.value in body and severity.value != expected_severity:
                raise UnsafeOutputError("Contradictory severity.")

    referral = context.immutable_facts.get("overall_referral")
    if referral == "لا" and any(
        phrase in body
        for phrase in ("يجب الإحالة", "ضرورة الإحالة", "يحتاج إلى أخصائي")
    ):
        raise UnsafeOutputError("Contradictory referral.")
    if referral == "نعم" and any(
        phrase in body
        for phrase in ("لا حاجة للإحالة", "لا يحتاج إلى أخصائي")
    ):
        raise UnsafeOutputError("Contradictory referral.")

    progress = context.immutable_facts.get("progress_percent")
    if isinstance(progress, int | float):
        if progress < 50 and any(
            phrase in body for phrase in ("تقدم واضح", "تحسن كبير")
        ):
            raise UnsafeOutputError("Contradictory progress.")
        if progress >= 75 and any(
            phrase in body for phrase in ("لم يحرز أي تقدم", "تراجع واضح")
        ):
            raise UnsafeOutputError("Contradictory progress.")

    allowed_percentages = {
        float(value)
        for key, value in context.immutable_facts.items()
        if key.endswith("_percent") and isinstance(value, int | float)
    }
    for match in _PERCENT.finditer(body):
        if float(match.group(1)) not in allowed_percentages:
            raise UnsafeOutputError("Invented percentage.")


def parse_and_validate(
    raw_json: str, context: AssistanceContext
) -> AssistanceContent:
    try:
        content = AssistanceContent.model_validate_json(raw_json)
    except (ValidationError, ValueError) as exc:
        raise InvalidOutputError("Invalid structured output.") from exc

    if content.disclaimer != DISCLAIMER_AR:
        raise UnsafeOutputError("The disclaimer was changed.")

    body = _content_body(content)
    lowered_body = body.casefold()
    if _URL_OR_MARKUP.search(body):
        raise UnsafeOutputError("Markup or external URL found.")
    if any(term in lowered_body for term in _FORBIDDEN_TERMS):
        raise UnsafeOutputError("Diagnostic or treatment wording found.")

    allowed_sources = {
        source.source_id: source for source in context.approved_sources
    }
    cited_sources = set(content.source_ids)
    if len(cited_sources) != len(content.source_ids):
        raise UngroundedOutputError("Duplicate source IDs.")
    if not cited_sources.issubset(allowed_sources):
        raise UngroundedOutputError("Unknown source ID.")

    action_sources = {
        source.source_id: source
        for source in context.approved_sources
        if source.supports_action_tip
    }
    for tip in content.action_tips:
        source = action_sources.get(tip.source_id)
        if source is None or tip.source_id not in cited_sources:
            raise UngroundedOutputError("Action tip has no approved source.")
        if source.title not in tip.text:
            raise UngroundedOutputError("Action tip omits the approved activity name.")

    mentioned_activity_ids = set(_ACTIVITY_ID.findall(body))
    if not mentioned_activity_ids.issubset(action_sources):
        raise UngroundedOutputError("Unknown activity ID in content.")

    _validate_immutable_facts(content, context)
    return content

