"""Opt-in live smoke test; excluded from normal and CI test runs."""
from __future__ import annotations

import os

import pytest

from app.ai.prompts import build_prompt
from app.ai.protocols import ProviderRequest
from app.ai.providers.gemini import GeminiAIProvider
from app.ai.schemas import (
    AssistanceContent,
    AssistanceContext,
    AssistanceOperation,
    GroundingRecord,
)
from app.ai.validators import parse_and_validate
from app.core.constants import DISCLAIMER_AR


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_GEMINI_TEST") != "1",
    reason="Set RUN_LIVE_GEMINI_TEST=1 for the opt-in live smoke test.",
)
async def test_live_gemini_structured_output_is_safe_and_grounded() -> None:
    api_key = os.getenv("GEMINI_API_KEY", "")
    model = os.getenv("GEMINI_MODEL", "")
    if not api_key or not model:
        pytest.skip("Live Gemini credentials and model are not configured.")

    context = AssistanceContext(
        operation=AssistanceOperation.WEEKLY_PLAN_SUMMARY,
        age_band="2 سنوات",
        immutable_facts={
            "is_active": True,
            "total_activities": 1,
            "completed_count": 0,
            "adherence_percent": 0.0,
            "weekly_goals": ["دعم الفهم"],
        },
        approved_sources=[
            GroundingRecord(
                source_id="A001",
                source_type="KB02_activity",
                title="لعبة الصور",
                excerpt="نشاط منزلي قصير لدعم الفهم.",
                supports_action_tip=True,
            )
        ],
    )
    provider = GeminiAIProvider(
        api_key=api_key,
        model=model,
        timeout_seconds=15,
        max_retries=1,
    )
    try:
        raw_json = await provider.generate(
            ProviderRequest(
                operation=context.operation,
                prompt=build_prompt(context, "v1"),
                context=context,
                response_schema=AssistanceContent,
            )
        )
        content = parse_and_validate(raw_json, context)
        assert content.disclaimer == DISCLAIMER_AR
        assert set(content.source_ids) <= {"A001"}
    finally:
        await provider.aclose()

