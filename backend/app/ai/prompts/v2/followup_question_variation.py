"""Prompt for AI-varied weekly follow-up question wording.

Gemini is given only a deterministic candidate list (each item already bound
to a real KB06 template and a real KB02 activity) and may only pick a 5-8
subset and reword the Arabic text — it never supplies domain, activity, or
scoring fields, so nothing it returns can affect KB06 mapping or scoring.
"""
from __future__ import annotations

import json

from app.schemas.followup import WeeklyFollowupQuestionResponse


def build(candidates: list[WeeklyFollowupQuestionResponse]) -> str:
    payload = [
        {
            "id": candidate.id,
            "domain": candidate.domain.value,
            "activity_name": candidate.activity_name,
            "original_wording_ar": candidate.question,
        }
        for candidate in candidates
    ]
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    return f"""أنت محرر عربي مساعد للوالدين داخل أداة دعم غير تشخيصية.

المهمة:
اختر بين 5 و8 أسئلة متابعة أسبوعية من قائمة المرشحين المعتمدة أدناه، وأعد صياغة
نص كل سؤال مختار بعربية واضحة وداعمة موجهة لولي الأمر، دون تغيير معناه أو
الموضوع الذي يقيسه.

قواعد إلزامية:
- أعد JSON فقط بالشكل: {{"questions": [{{"id": "...", "wording_ar": "..."}}]}}
  بلا أي حقول أخرى، وبلا Markdown أو HTML.
- اختر بين 5 و8 عناصر فقط من معرّفات id الموجودة في قائمة المرشحين. لا تخترع
  معرّفاً جديداً ولا تكرر نفس المعرّف مرتين.
- لا تغيّر الموضوع أو المهارة أو النشاط الذي يقيسه السؤال الأصلي — أعد الصياغة
  فقط، واجعل الصياغة الجديدة مختلفة عن original_wording_ar وعن باقي الأسئلة
  المختارة حتى لا تتكرر.
- لا تشخّص، ولا تصف مرضاً أو حالة، ولا تقترح دواءً أو جرعةً أو علاجاً.
- لا تعد بنتيجة أو تحسّن مؤكد؛ اكتب سؤالاً محايداً عن سلوك الطفل الحالي فقط.
- لا تذكر رابطاً أو Markdown أو رمزاً برمجياً.

قائمة المرشحين المعتمدة (اختر منها فقط):
{payload_json}
"""
