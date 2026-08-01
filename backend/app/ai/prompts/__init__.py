"""Versioned prompt registry."""
from __future__ import annotations

from app.ai.prompts.v1 import (
    assessment_explanation,
    followup_summary,
    weekly_plan_summary,
)
from app.ai.schemas import AssistanceContext, AssistanceOperation


def build_prompt(context: AssistanceContext, version: str) -> str:
    if version != "v1":
        raise ValueError("Unsupported AI prompt version.")

    builders = {
        AssistanceOperation.ASSESSMENT_EXPLANATION: assessment_explanation.build,
        AssistanceOperation.WEEKLY_PLAN_SUMMARY: weekly_plan_summary.build,
        AssistanceOperation.FOLLOWUP_SUMMARY: followup_summary.build,
    }
    return builders[context.operation](context)
