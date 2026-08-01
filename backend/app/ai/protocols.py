"""Provider-neutral interface for optional assisted wording."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from app.ai.schemas import AssistanceContext, AssistanceOperation, FallbackReason


@dataclass(frozen=True)
class ProviderRequest:
    operation: AssistanceOperation
    prompt: str
    context: AssistanceContext
    # The exact Pydantic model the provider's JSON output must satisfy for
    # this operation — narrative wording (`AssistanceContent`) and the
    # structured Milestone-3 operations (follow-up question wording, activity
    # explanations) each have a different output shape, so this can't be
    # hardcoded provider-side (see `providers/gemini.py`).
    response_schema: type[BaseModel]


class ProviderError(Exception):
    """A provider failure safe to classify without exposing provider details."""


class ProviderTimeoutError(ProviderError):
    """The provider did not respond before the configured deadline."""


class ProviderUnavailableError(ProviderError):
    def __init__(self, reason: FallbackReason) -> None:
        self.reason = reason
        super().__init__(reason.value)


class AIProvider(Protocol):
    name: str

    async def generate(self, request: ProviderRequest) -> str:
        """Return one JSON object matching ``AssistanceContent``."""
        ...

    async def aclose(self) -> None:
        """Release provider resources."""
        ...
