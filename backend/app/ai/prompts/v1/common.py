"""Shared safety envelope for v1 Arabic assistance prompts."""
from __future__ import annotations

import json

from app.ai.schemas import AssistanceContext
from app.core.constants import DISCLAIMER_AR


def render(context: AssistanceContext, objective: str) -> str:
    payload = json.dumps(
        context.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"""أنت محرر عربي مساعد للوالدين داخل أداة دعم غير تشخيصية.

المهمة:
{objective}

قواعد إلزامية:
- أعد JSON فقط وفق مخطط الاستجابة المفروض من الخادم، بلا Markdown أو HTML.
- الحقائق الحتمية immutable_facts نهائية. لا تغيرها ولا تناقضها.
- لا تستنتج درجة أو شدة أو إحالة أو أهلية جديدة.
- استخدم approved_sources فقط. لا تخترع نشاطاً أو مصدراً أو اقتباساً أو رابطاً.
- كل action_tip يجب أن يذكر اسم النشاط المعتمد حرفياً وأن يحمل source_id لذلك النشاط.
- source_ids يجب أن تكون مجموعة فرعية من معرّفات approved_sources المستخدمة فعلاً.
- لا تشخّص، ولا تصف مرضاً، ولا تقترح دواءً أو جرعةً أو علاجاً.
- لا تطلب أو تستنتج اسماً أو بريداً أو معرّف مستخدم/طفل/مورد أو تاريخاً طبياً.
- اكتب بالعربية الواضحة والداعمة، بجمل قصيرة، وبحد أقصى ثلاث نصائح عملية.
- ضع نص التنبيه التالي حرفياً في disclaimer:
{DISCLAIMER_AR}

السياق المصغّر المعتمد:
{payload}
"""
