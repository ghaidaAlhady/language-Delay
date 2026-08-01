"""Weekly-plan summary prompt v1."""
from __future__ import annotations

from app.ai.prompts.v1.common import render
from app.ai.schemas import AssistanceContext


def build(context: AssistanceContext) -> str:
    return render(
        context,
        (
            "لخّص الخطة الأسبوعية الحتمية دون إضافة أنشطة أو تعديلها، واشرح للوالد "
            "كيف يبدأ بعدد قليل من أنشطة KB02 الموجودة في السياق."
        ),
    )
