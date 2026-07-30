"""Provider-neutral interface for optional assisted wording."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.ai.schemas import AssistanceContext, AssistanceOperation, FallbackReason


@dataclass(frozen=True)
class ProviderRequest:
    operation: AssistanceOperation
    prompt: str
    context: AssistanceContext


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
