"""AI-assisted "افهم أكثر" explanation for one approved KB02 activity.

Context is built from a single `ActivityRecord` only — no child, parent, or
session data is ever read to build it (see `prompts/v2/activity_explanation
.build`), so the "never send" list in the Milestone 3 spec is satisfied by
construction, not by redaction after the fact.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass

from pydantic import ValidationError

from app.ai.prompts.v2 import activity_explanation as prompt_builder
from app.ai.protocols import (
    AIProvider,
    ProviderError,
    ProviderRequest,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.ai.schemas import (
    ActivityExplanationContent,
    ActivityExplanationResponse,
    AssistanceContext,
    AssistanceOperation,
    ExampleDialogue,
    FallbackReason,
    GenerationSource,
    GroundingRecord,
)
from app.ai.source_labels import build_source_references
from app.core.config import Settings
from app.core.logging import get_logger
from app.rag.schemas import ActivityRecord

logger = get_logger(__name__)

PROMPT_VERSION = "v2"

_URL_OR_MARKUP = re.compile(r"https?://|www\.|```|<[^>]+>", re.IGNORECASE)
_ACTIVITY_ID = re.compile(r"\bA\d{3,}\b", re.IGNORECASE)
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
_GUARANTEE_TERMS = (
    "مضمون",
    "سيتحسن حتماً",
    "سيتحسن بالتأكيد",
    "بالتأكيد سيتعلم",
    "ستتخلص",
)


class InvalidActivityExplanationOutputError(Exception):
    """The provider returned malformed or contract-breaking output."""


class UnsafeActivityExplanationOutputError(Exception):
    """The provider returned unsafe or contradictory wording."""


class UngroundedActivityExplanationOutputError(Exception):
    """The provider referenced an activity other than the one requested."""


def _content_body(content: ActivityExplanationContent) -> str:
    return " ".join(
        [
            content.title_ar,
            content.simple_explanation_ar,
            content.purpose_ar,
            *content.steps_ar,
            content.example_dialogue.parent_text,
            content.example_dialogue.example_child_response,
            content.example_dialogue.supportive_parent_continuation,
            content.alternative_ar,
        ]
    )


def _validate(raw_json: str, activity: ActivityRecord) -> ActivityExplanationContent:
    try:
        content = ActivityExplanationContent.model_validate_json(raw_json)
    except (ValidationError, ValueError) as exc:
        raise InvalidActivityExplanationOutputError("Invalid structured output.") from exc

    if content.activity_id != activity.id:
        raise UngroundedActivityExplanationOutputError(
            "Response activity_id does not match the requested activity."
        )

    body = _content_body(content)
    lowered = body.casefold()
    if _URL_OR_MARKUP.search(body):
        raise UnsafeActivityExplanationOutputError("Markup or external URL found.")
    if any(term in lowered for term in _FORBIDDEN_TERMS):
        raise UnsafeActivityExplanationOutputError(
            "Diagnostic or treatment wording found."
        )
    if any(term in lowered for term in _GUARANTEE_TERMS):
        raise UnsafeActivityExplanationOutputError("Guaranteed-outcome wording found.")

    allowed_ids = {activity.id}
    if not set(content.source_ids).issubset(allowed_ids):
        raise UngroundedActivityExplanationOutputError("Unknown source ID.")
    mentioned_activity_ids = set(_ACTIVITY_ID.findall(body))
    if not mentioned_activity_ids.issubset(allowed_ids):
        raise UngroundedActivityExplanationOutputError(
            "A different activity ID was mentioned."
        )

    return content


def _fallback_steps(activity: ActivityRecord) -> list[str]:
    steps = []
    if activity.tools:
        steps.append(f"جهّزوا: {activity.tools}.")
    steps.append(activity.parent_instructions)
    steps.append(f"كرّروا النشاط لمدة {activity.duration} بمعدل {activity.frequency}.")
    return steps[:5] if len(steps) >= 3 else steps + [activity.expected_outcome]


def build_deterministic_fallback(activity: ActivityRecord) -> ActivityExplanationContent:
    return ActivityExplanationContent(
        activity_id=activity.id,
        title_ar=activity.name,
        simple_explanation_ar=activity.description,
        purpose_ar=activity.goal,
        steps_ar=_fallback_steps(activity),
        example_dialogue=ExampleDialogue(
            parent_text=f"هيا نجرّب «{activity.name}» معًا.",
            example_child_response=(
                "قد يشارك الطفل بمحاولة بسيطة أو باهتمام صامت — هذا مثال محتمل فقط."
            ),
            supportive_parent_continuation="شجّعوا أي محاولة، وكرروا النشاط بهدوء دون ضغط.",
        ),
        alternative_ar=(
            f"إذا لم يستجب الطفل، بسّطوا «{activity.name}»: قلّلوا عدد الخيارات أو "
            "المدة، واستخدموا نبرة أهدأ وتلميحات أوضح، مع الحفاظ على هدف النشاط نفسه."
        ),
        source_ids=[activity.id],
    )


def _build_context(activity: ActivityRecord) -> AssistanceContext:
    return AssistanceContext(
        operation=AssistanceOperation.ACTIVITY_EXPLANATION,
        age_band=f"{activity.age} سنوات",
        immutable_facts={
            "activity_id": activity.id,
            "domain": activity.domain.value,
            "duration": activity.duration,
            "frequency": activity.frequency,
        },
        approved_sources=[
            GroundingRecord(
                source_id=activity.id,
                source_type="KB02_activity",
                title=activity.name,
                excerpt=(
                    f"الهدف: {activity.goal}. الوصف: {activity.description}. "
                    f"الإرشادات: {activity.parent_instructions}. "
                    f"الأدوات: {activity.tools}."
                ),
                supports_action_tip=True,
            )
        ],
    )


@dataclass
class ActivityExplanationOrchestrator:
    provider: AIProvider
    settings: Settings

    async def generate(
        self, *, activity: ActivityRecord, correlation_id: str
    ) -> ActivityExplanationResponse:
        started_at = time.perf_counter()
        reason: FallbackReason | None = None
        content: ActivityExplanationContent | None = None
        context = _build_context(activity)

        prompt = prompt_builder.build(activity)
        request = ProviderRequest(
            operation=AssistanceOperation.ACTIVITY_EXPLANATION,
            prompt=prompt,
            context=context,
            response_schema=ActivityExplanationContent,
        )
        try:
            raw_json = await self.provider.generate(request)
            content = _validate(raw_json, activity)
        except ProviderUnavailableError as exc:
            reason = exc.reason
        except ProviderTimeoutError:
            reason = FallbackReason.TIMEOUT
        except ProviderError:
            reason = FallbackReason.PROVIDER_ERROR
        except InvalidActivityExplanationOutputError:
            reason = FallbackReason.INVALID_OUTPUT
        except UnsafeActivityExplanationOutputError:
            reason = FallbackReason.UNSAFE_OUTPUT
        except UngroundedActivityExplanationOutputError:
            reason = FallbackReason.UNGROUNDED_OUTPUT

        if content is None:
            content = build_deterministic_fallback(activity)
            source = GenerationSource.DETERMINISTIC_FALLBACK
            outcome = "fallback"
        else:
            source = GenerationSource.GEMINI
            outcome = "generated"

        logger.info(
            "ai_activity_explanation_completed",
            correlation_id=correlation_id,
            operation=AssistanceOperation.ACTIVITY_EXPLANATION.value,
            prompt_version=PROMPT_VERSION,
            provider=self.provider.name,
            latency_ms=round((time.perf_counter() - started_at) * 1000, 2),
            outcome=outcome,
            fallback_reason=reason.value if reason else None,
        )
        return ActivityExplanationResponse(
            content=content,
            generation_source=source,
            fallback_reason=reason,
            prompt_version=PROMPT_VERSION,
            source_references=build_source_references(
                content.source_ids, context.approved_sources
            ),
        )
