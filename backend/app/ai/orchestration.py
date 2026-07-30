"""Safe orchestration: context -> prompt -> provider -> validation -> fallback."""
from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context_builder import AssistanceContextBuilder
from app.ai.fallback import build_deterministic_fallback
from app.ai.prompts import build_prompt
from app.ai.protocols import (
    AIProvider,
    ProviderError,
    ProviderRequest,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.ai.schemas import (
    AssistanceContext,
    AssistanceResponse,
    FallbackReason,
    GenerationSource,
)
from app.ai.validators import (
    InvalidOutputError,
    UngroundedOutputError,
    UnsafeOutputError,
    parse_and_validate,
)
from app.core.config import Settings
from app.core.logging import get_logger
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository

logger = get_logger(__name__)


@dataclass
class AIAssistanceService:
    session: AsyncSession
    kb: KnowledgeBaseRepository
    provider: AIProvider
    settings: Settings

    async def assessment_explanation(
        self, *, assessment_id: str, user_id: str, correlation_id: str
    ) -> AssistanceResponse:
        context = await self._builder.for_assessment(
            assessment_id=assessment_id, user_id=user_id
        )
        return await self._generate(context, correlation_id)

    async def weekly_plan_summary(
        self, *, weekly_plan_id: str, user_id: str, correlation_id: str
    ) -> AssistanceResponse:
        context = await self._builder.for_weekly_plan(
            weekly_plan_id=weekly_plan_id, user_id=user_id
        )
        return await self._generate(context, correlation_id)

    async def followup_summary(
        self, *, followup_id: str, user_id: str, correlation_id: str
    ) -> AssistanceResponse:
        context = await self._builder.for_followup(
            followup_id=followup_id, user_id=user_id
        )
        return await self._generate(context, correlation_id)

    @property
    def _builder(self) -> AssistanceContextBuilder:
        return AssistanceContextBuilder(session=self.session, kb=self.kb)

    async def _generate(
        self, context: AssistanceContext, correlation_id: str
    ) -> AssistanceResponse:
        started_at = time.perf_counter()
        reason: FallbackReason | None = None
        content = None

        if not context.approved_sources:
            reason = FallbackReason.EMPTY_CONTEXT
        else:
            prompt = build_prompt(
                context, self.settings.gemini_prompt_version
            )
            request = ProviderRequest(
                operation=context.operation,
                prompt=prompt,
                context=context,
            )
            try:
                raw_json = await self.provider.generate(request)
                content = parse_and_validate(raw_json, context)
            except ProviderUnavailableError as exc:
                reason = exc.reason
            except ProviderTimeoutError:
                reason = FallbackReason.TIMEOUT
            except ProviderError:
                reason = FallbackReason.PROVIDER_ERROR
            except InvalidOutputError:
                reason = FallbackReason.INVALID_OUTPUT
            except UnsafeOutputError:
                reason = FallbackReason.UNSAFE_OUTPUT
            except UngroundedOutputError:
                reason = FallbackReason.UNGROUNDED_OUTPUT

        if content is None:
            content = build_deterministic_fallback(context)
            source = GenerationSource.DETERMINISTIC_FALLBACK
            outcome = "fallback"
        else:
            source = GenerationSource.GEMINI
            outcome = "generated"

        logger.info(
            "ai_assistance_completed",
            correlation_id=correlation_id,
            operation=context.operation.value,
            prompt_version=self.settings.gemini_prompt_version,
            provider=self.provider.name,
            latency_ms=round((time.perf_counter() - started_at) * 1000, 2),
            outcome=outcome,
            approved_source_count=len(context.approved_sources),
            action_tip_count=len(content.action_tips),
            fallback_reason=reason.value if reason else None,
        )
        return AssistanceResponse(
            content=content,
            generation_source=source,
            fallback_reason=reason,
            prompt_version=self.settings.gemini_prompt_version,
        )
