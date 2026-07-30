"""Assessment explanation prompt v1."""
from __future__ import annotations

from app.ai.prompts.v1.common import render
from app.ai.schemas import AssistanceContext


def build(context: AssistanceContext) -> str:
    return render(
        context,
        (
            "بسّط نتيجة التقييم الحتمية للوالد، وأبرز نقاط القوة واحتياجات الدعم "
            "كما وردت فقط، ثم اقترح خطوات منزلية من أنشطة KB02 المعتمدة."
        ),
    )
