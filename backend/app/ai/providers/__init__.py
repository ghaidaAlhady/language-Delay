"""Provider construction with production-safe defaults."""
from __future__ import annotations

from app.ai.protocols import AIProvider
from app.ai.providers.disabled import DisabledAIProvider
from app.ai.providers.fake import FakeAIProvider
from app.ai.providers.gemini import GeminiAIProvider
from app.ai.schemas import FallbackReason
from app.core.config import Settings


def build_ai_provider(settings: Settings) -> AIProvider:
    """Select a provider without ever enabling a test double in production."""
    if settings.app_env == "e2e" and settings.ai_test_provider == "fake":
        return FakeAIProvider()
    if not settings.gemini_enabled:
        return DisabledAIProvider(FallbackReason.DISABLED)
    if not settings.gemini_configured:
        return DisabledAIProvider(FallbackReason.NOT_CONFIGURED)
    return GeminiAIProvider(
        api_key=settings.gemini_api_key.get_secret_value(),
        model=settings.gemini_model,
        timeout_seconds=settings.gemini_timeout_seconds,
        max_retries=settings.gemini_max_retries,
    )
