"""Disabled provider used by default and for incomplete configuration."""
from __future__ import annotations

from app.ai.protocols import ProviderRequest, ProviderUnavailableError
from app.ai.schemas import FallbackReason


class DisabledAIProvider:
    name = "disabled"

    def __init__(self, reason: FallbackReason) -> None:
        self._reason = reason

    async def generate(self, _request: ProviderRequest) -> str:
        raise ProviderUnavailableError(self._reason)

    async def aclose(self) -> None:
        return None

