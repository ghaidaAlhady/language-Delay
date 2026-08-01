"""AI-varied wording for weekly follow-up questions.

Selection and KB06/scoring mapping stay deterministic. Gemini may only choose
a 5-8 item subset of the approved candidates and vary Arabic wording. The API
layer persists the first validated result on ``weekly_plans`` so refreshes,
process restarts, and multi-worker deployments return the exact same question
set. The small in-process cache below is only an optimization and is never the
source of durability.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.ai.prompts.v2 import followup_question_variation
from app.ai.protocols import (
    AIProvider,
    ProviderError,
    ProviderRequest,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.ai.schemas import (
    AssistanceContext,
    AssistanceOperation,
    FallbackReason,
    GenerationSource,
    GroundingRecord,
)
from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.followup import WeeklyFollowupQuestionResponse

logger = get_logger(__name__)

MIN_QUESTIONS = 5
MAX_QUESTIONS = 8
PROMPT_VERSION = "v2"

# Reused verbatim from `app.ai.validators` conventions (kept local to avoid a
# reverse dependency from that module onto this one).
_URL_OR_MARKUP = re.compile(r"https?://|www\.|```|<[^>]+>", re.IGNORECASE)
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


class InvalidFollowupQuestionsOutputError(Exception):
    """The provider returned malformed or contract-breaking output."""


class UnsafeFollowupQuestionsOutputError(Exception):
    """The provider returned unsafe, duplicate, or contradictory wording."""


class UngroundedFollowupQuestionsOutputError(Exception):
    """The provider selected an id outside the approved candidate pool."""


class _GeminiSelectedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=20)
    wording_ar: str = Field(min_length=1, max_length=280)


class _GeminiFollowupQuestionsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[_GeminiSelectedQuestion] = Field(
        min_length=MIN_QUESTIONS, max_length=MAX_QUESTIONS
    )


@dataclass(frozen=True)
class FollowupQuestionsResult:
    questions: list[WeeklyFollowupQuestionResponse]
    generation_source: GenerationSource
    fallback_reason: FallbackReason | None


def _validate_and_merge(
    raw_json: str,
    candidates_by_id: dict[str, WeeklyFollowupQuestionResponse],
) -> list[WeeklyFollowupQuestionResponse]:
    try:
        parsed = _GeminiFollowupQuestionsOutput.model_validate_json(raw_json)
    except (ValidationError, ValueError) as exc:
        raise InvalidFollowupQuestionsOutputError("Invalid structured output.") from exc

    seen_ids: set[str] = set()
    seen_normalized_wording: set[str] = set()
    merged: list[WeeklyFollowupQuestionResponse] = []
    for item in parsed.questions:
        if item.id not in candidates_by_id:
            raise UngroundedFollowupQuestionsOutputError(
                f"Selected id outside the approved candidate pool: {item.id!r}"
            )
        if item.id in seen_ids:
            raise InvalidFollowupQuestionsOutputError("Duplicate selected id.")
        seen_ids.add(item.id)

        wording = item.wording_ar.strip()
        if not wording:
            raise InvalidFollowupQuestionsOutputError("Empty wording.")
        lowered = wording.casefold()
        if _URL_OR_MARKUP.search(wording):
            raise UnsafeFollowupQuestionsOutputError("Markup or external URL found.")
        if any(term in lowered for term in _FORBIDDEN_TERMS):
            raise UnsafeFollowupQuestionsOutputError(
                "Diagnostic or treatment wording found."
            )
        if any(term in lowered for term in _GUARANTEE_TERMS):
            raise UnsafeFollowupQuestionsOutputError("Guaranteed-outcome wording found.")

        normalized = " ".join(wording.split()).casefold()
        if normalized in seen_normalized_wording:
            raise UnsafeFollowupQuestionsOutputError(
                "Duplicate or near-duplicate wording."
            )
        seen_normalized_wording.add(normalized)

        candidate = candidates_by_id[item.id]
        merged.append(candidate.model_copy(update={"question": wording}))

    return merged


def _candidate_context(candidates: list[WeeklyFollowupQuestionResponse]) -> AssistanceContext:
    """Reuse `AssistanceContext`/`ProviderRequest` unchanged for this operation
    by representing each deterministic candidate as an approved source — the
    same pattern `context_builder.py::for_followup` already uses for KB06
    question grounding."""
    sources = [
        GroundingRecord(
            source_id=candidate.id,
            source_type="KB06_followup_candidate",
            title=candidate.domain.value,
            excerpt=candidate.question,
        )
        for candidate in candidates
    ]
    return AssistanceContext(
        operation=AssistanceOperation.FOLLOWUP_QUESTION_VARIATION,
        age_band=f"{candidates[0].age} سنوات" if candidates else "غير محدد",
        immutable_facts={
            "min_questions": MIN_QUESTIONS,
            "max_questions": MAX_QUESTIONS,
            "candidate_count": len(candidates),
        },
        approved_sources=sources,
    )


# In-process optimization only. The API layer persists the frozen winner in
# the database before returning it to the client.
_CACHE: dict[str, FollowupQuestionsResult] = {}


def clear_cached_questions(weekly_plan_id: str) -> None:
    _CACHE.pop(weekly_plan_id, None)


@dataclass
class FollowupQuestionOrchestrator:
    provider: AIProvider
    settings: Settings

    async def generate(
        self,
        *,
        weekly_plan_id: str,
        candidates: list[WeeklyFollowupQuestionResponse],
        correlation_id: str,
    ) -> FollowupQuestionsResult:
        cached = _CACHE.get(weekly_plan_id)
        if cached is not None:
            return cached

        result = await self._generate_uncached(candidates, correlation_id)
        _CACHE[weekly_plan_id] = result
        return result

    async def _generate_uncached(
        self,
        candidates: list[WeeklyFollowupQuestionResponse],
        correlation_id: str,
    ) -> FollowupQuestionsResult:
        started_at = time.perf_counter()
        reason: FallbackReason | None = None
        questions: list[WeeklyFollowupQuestionResponse] | None = None
        candidates_by_id = {candidate.id: candidate for candidate in candidates}

        if len(candidates) < MIN_QUESTIONS:
            reason = FallbackReason.EMPTY_CONTEXT
        else:
            context = _candidate_context(candidates)
            prompt = followup_question_variation.build(candidates)
            request = ProviderRequest(
                operation=AssistanceOperation.FOLLOWUP_QUESTION_VARIATION,
                prompt=prompt,
                context=context,
                response_schema=_GeminiFollowupQuestionsOutput,
            )
            try:
                raw_json = await self.provider.generate(request)
                questions = _validate_and_merge(raw_json, candidates_by_id)
            except ProviderUnavailableError as exc:
                reason = exc.reason
            except ProviderTimeoutError:
                reason = FallbackReason.TIMEOUT
            except ProviderError:
                reason = FallbackReason.PROVIDER_ERROR
            except InvalidFollowupQuestionsOutputError:
                reason = FallbackReason.INVALID_OUTPUT
            except UnsafeFollowupQuestionsOutputError:
                reason = FallbackReason.UNSAFE_OUTPUT
            except UngroundedFollowupQuestionsOutputError:
                reason = FallbackReason.UNGROUNDED_OUTPUT

        if questions is None:
            # Deterministic fallback: the original KB06-worded candidates,
            # verbatim, capped to MAX_QUESTIONS — this path cannot fail, since
            # `select_weekly_followup_questions` already guarantees >=5.
            questions = [
                candidate.model_copy(
                    update={
                        "linked_activity_ids": [candidate.activity_id],
                        "source_ids": list(
                            dict.fromkeys(
                                [candidate.activity_id, candidate.source_question_id]
                            )
                        ),
                        "prompt_version": PROMPT_VERSION,
                    }
                )
                for candidate in candidates[:MAX_QUESTIONS]
            ]
            source = GenerationSource.DETERMINISTIC_FALLBACK
            outcome = "fallback"
        else:
            questions = [
                question.model_copy(
                    update={
                        "linked_activity_ids": [question.activity_id],
                        "source_ids": list(
                            dict.fromkeys(
                                [question.activity_id, question.source_question_id]
                            )
                        ),
                        "prompt_version": PROMPT_VERSION,
                    }
                )
                for question in questions
            ]
            source = GenerationSource.GEMINI
            outcome = "generated"

        logger.info(
            "ai_followup_questions_completed",
            correlation_id=correlation_id,
            operation=AssistanceOperation.FOLLOWUP_QUESTION_VARIATION.value,
            prompt_version=PROMPT_VERSION,
            provider=self.provider.name,
            latency_ms=round((time.perf_counter() - started_at) * 1000, 2),
            outcome=outcome,
            candidate_count=len(candidates),
            selected_count=len(questions),
            fallback_reason=reason.value if reason else None,
        )
        return FollowupQuestionsResult(
            questions=questions, generation_source=source, fallback_reason=reason
        )
