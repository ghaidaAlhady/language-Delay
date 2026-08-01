"""Weekly follow-up progress summary prompt v1."""
from __future__ import annotations

from app.ai.prompts.v1.common import render
from app.ai.schemas import AssistanceContext


def build(context: AssistanceContext) -> str:
    return render(
        context,
        (
            "لخّص نتيجة المتابعة الأسبوعية الحتمية كما هي، واذكر التقدم ومجالات "
            "الدعم والهدف التالي دون استنتاج نتيجة جديدة، مع نصائح من الأنشطة المعتمدة فقط."
        ),
    )
