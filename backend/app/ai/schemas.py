"""Strict contracts shared by AI context building, providers, and the API."""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AssistanceOperation(StrEnum):
    ASSESSMENT_EXPLANATION = "assessment_explanation"
    WEEKLY_PLAN_SUMMARY = "weekly_plan_summary"
    FOLLOWUP_SUMMARY = "followup_summary"


class GenerationSource(StrEnum):
    GEMINI = "gemini"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"


class FallbackReason(StrEnum):
    DISABLED = "disabled"
    NOT_CONFIGURED = "not_configured"
    EMPTY_CONTEXT = "empty_context"
    TIMEOUT = "timeout"
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


class AssistanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: AssistanceContent
    generation_source: GenerationSource
    fallback_reason: FallbackReason | None = None
    prompt_version: str = Field(min_length=1, max_length=20)

