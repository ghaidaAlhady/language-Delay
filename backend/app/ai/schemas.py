"""Strict contracts shared by AI context building, providers, and the API."""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AssistanceOperation(StrEnum):
    ASSESSMENT_EXPLANATION = "assessment_explanation"
    WEEKLY_PLAN_SUMMARY = "weekly_plan_summary"
    FOLLOWUP_SUMMARY = "followup_summary"
    # Milestone 3: structured operations with their own output schema (not
    # `AssistanceContent`) — see `app/ai/followup_questions.py` and
    # `app/ai/activity_explanation.py`. Listed here only as a shared routing/
    # logging tag, consistent with the three operations above.
    FOLLOWUP_QUESTION_VARIATION = "followup_question_variation"
    ACTIVITY_EXPLANATION = "activity_explanation"


class GenerationSource(StrEnum):
    GEMINI = "gemini"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"


class FallbackReason(StrEnum):
    DISABLED = "disabled"
    NOT_CONFIGURED = "not_configured"
    EMPTY_CONTEXT = "empty_context"
    TIMEOUT = "timeout"
    PROVIDER_TIMEOUT = "provider_timeout"
    QUOTA_EXHAUSTED = "quota_exhausted"
    RATE_LIMITED = "rate_limited"
    AUTHENTICATION_ERROR = "authentication_error"
    PERMISSION_ERROR = "permission_error"
    MODEL_UNAVAILABLE = "model_unavailable"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_ERROR = "provider_error"
    INVALID_OUTPUT = "invalid_output"
    UNSAFE_OUTPUT = "unsafe_output"
    UNGROUNDED_OUTPUT = "ungrounded_output"


class GroundingRecord(BaseModel):
    """A minimized, approved knowledge-base record safe to send externally."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1, max_length=40)
    source_type: str = Field(min_length=1, max_length=30)
    title: str = Field(min_length=1, max_length=160)
    excerpt: str = Field(min_length=1, max_length=700)
    supports_action_tip: bool = False


FactValue = str | int | float | bool | list[str]


class AssistanceContext(BaseModel):
    """Sanitized facts built only after resource ownership is established."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: AssistanceOperation
    age_band: str = Field(min_length=1, max_length=30)
    immutable_facts: dict[str, FactValue]
    approved_sources: list[GroundingRecord] = Field(max_length=24)


class ActionTip(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=240)
    source_id: str = Field(min_length=1, max_length=40)


class AssistanceContent(BaseModel):
    """The only provider output shape accepted by the application."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=90)
    summary: str = Field(min_length=1, max_length=700)
    encouragement: str = Field(min_length=1, max_length=240)
    action_tips: list[ActionTip] = Field(default_factory=list, max_length=3)
    disclaimer: str = Field(min_length=1, max_length=400)
    source_ids: list[str] = Field(default_factory=list, max_length=12)


class SourceReference(BaseModel):
    """A human-readable, KB-resolved label for a `source_id` — never provider
    -supplied, always assembled server-side from the approved context so
    Gemini can neither invent nor override a label (Milestone 3 §4)."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=40)
    label_ar: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=40)


class AssistanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: AssistanceContent
    generation_source: GenerationSource
    fallback_reason: FallbackReason | None = None
    prompt_version: str = Field(min_length=1, max_length=20)
    # Additive, backward-compatible: human-readable labels for `content
    # .source_ids`, resolved server-side from the approved context — see
    # `SourceReference`. Empty for any id that couldn't be resolved; the
    # frontend falls back to a neutral label in that case.
    source_references: list[SourceReference] = Field(default_factory=list)


class ExampleDialogue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_text: str = Field(min_length=1, max_length=240)
    example_child_response: str = Field(min_length=1, max_length=240)
    supportive_parent_continuation: str = Field(min_length=1, max_length=240)


class ActivityExplanationContent(BaseModel):
    """The only provider output shape accepted for an activity explanation."""

    model_config = ConfigDict(extra="forbid")

    activity_id: str = Field(min_length=1, max_length=20)
    title_ar: str = Field(min_length=1, max_length=90)
    simple_explanation_ar: str = Field(min_length=1, max_length=500)
    purpose_ar: str = Field(min_length=1, max_length=300)
    steps_ar: list[str] = Field(min_length=3, max_length=5)
    example_dialogue: ExampleDialogue
    alternative_ar: str = Field(min_length=1, max_length=500)
    source_ids: list[str] = Field(default_factory=list, max_length=8)


class ActivityExplanationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: ActivityExplanationContent
    generation_source: GenerationSource
    fallback_reason: FallbackReason | None = None
    prompt_version: str = Field(min_length=1, max_length=20)
    source_references: list[SourceReference] = Field(default_factory=list)

