"""Typed, validated representations of records loaded from KB01-KB05.

Every record keeps a reference back to its knowledge-base source (file,
sheet, and natural ID) so that any recommendation, score, or report text
produced downstream remains traceable to the exact KB row it came from.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Domain(StrEnum):
    RECEPTIVE_LANGUAGE = "اللغة الاستقبالية"
    EXPRESSIVE_LANGUAGE = "اللغة التعبيرية"
    COMMUNICATION_SOCIAL = "التواصل والمهارات الاجتماعية"
    SPEECH = "النطق"


class Importance(StrEnum):
    ESSENTIAL = "أساسي"
    IMPORTANT = "مهم"
    SUPPORTIVE = "داعم"


class Severity(StrEnum):
    NORMAL = "طبيعي"
    MILD_DELAY = "تأخر بسيط"
    MODERATE_DELAY = "تأخر متوسط"
    NOTABLE_DELAY = "تأخر ملحوظ"


#: Ascending order of concern used for aggregating per-domain severities into
#: a single overall severity (worst-domain-wins, the safest choice).
SEVERITY_ORDER: list[Severity] = [
    Severity.NORMAL,
    Severity.MILD_DELAY,
    Severity.MODERATE_DELAY,
    Severity.NOTABLE_DELAY,
]


class ReportStatus(StrEnum):
    """Severity plus the follow-up-only 'improved' narrative status."""

    NORMAL = "طبيعي"
    MILD_DELAY = "تأخر بسيط"
    MODERATE_DELAY = "تأخر متوسط"
    NOTABLE_DELAY = "تأخر ملحوظ"
    IMPROVED = "تحسن"


class ReferralGuidance(StrEnum):
    NO = "لا"
    CONSIDER = "يُنظر في الإحالة"
    YES = "نعم"


#: Ascending order of urgency used for aggregating per-domain referral flags.
REFERRAL_ORDER: list[ReferralGuidance] = [
    ReferralGuidance.NO,
    ReferralGuidance.CONSIDER,
    ReferralGuidance.YES,
]


class KBRecordBase(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_file: str
    source_sheet: str


class MilestoneRecord(KBRecordBase):
    """KB01: an age-based language milestone/criterion."""

    id: str
    age: int
    domain: Domain
    skill: str
    criterion_description: str
    assessment_question: str
    expected_development: str
    importance: Importance
    reference: str


class ReferenceRecord(KBRecordBase):
    """KB01 References sheet: a cited scientific source (e.g. ASHA, CDC)."""

    code: str
    description: str


class ActivityRecord(KBRecordBase):
    """KB02: a home activity."""

    id: str
    name: str
    age: int
    domain: Domain
    target_skill: str
    goal: str
    description: str
    tools: str
    duration: str
    frequency: str
    difficulty: str
    parent_instructions: str
    expected_outcome: str
    reference: str


class DecisionRuleRecord(KBRecordBase):
    """KB03: a scoring-band decision rule for one (age, domain) pair."""

    id: str
    age: int
    domain: Domain
    score_condition: str
    score_threshold: float
    severity: Severity
    ai_recommendation: str
    suggested_activity_ids: list[str]
    follow_up: str
    referral: ReferralGuidance
    reference: str


class QuestionRecord(KBRecordBase):
    """KB05: an assessment question."""

    id: str
    age: int
    domain: Domain
    question: str
    answer_type: str
    yes_score: float
    no_score: float
    linked_milestone_id: str
    linked_rule_ids: list[str]
    notes: str | None = None


class ReportTemplateField(KBRecordBase):
    """KB04 key/value template sheets (initial, progress, referral reports)."""

    field_name: str
    value_description: str


class WeeklyPlanTemplateDay(KBRecordBase):
    """KB04 weekly-plan template row (illustrative field layout only)."""

    day: str
    activity_slot: str
    activity_name: str
    duration: str
    goal: str


class NarrativeTemplate(KBRecordBase):
    """KB04 status-keyed narrative template used for deterministic reports."""

    template_id: str
    status: ReportStatus
    text: str


class KnowledgeBase(BaseModel):
    """The fully loaded, validated, in-memory knowledge base (KB01-KB05)."""

    model_config = ConfigDict(frozen=True)

    milestones: list[MilestoneRecord]
    references: list[ReferenceRecord]
    activities: list[ActivityRecord]
    decision_rules: list[DecisionRuleRecord]
    questions: list[QuestionRecord]
    initial_report_fields: list[ReportTemplateField]
    progress_report_fields: list[ReportTemplateField]
    referral_report_fields: list[ReportTemplateField]
    weekly_plan_template: list[WeeklyPlanTemplateDay]
    narrative_templates: list[NarrativeTemplate]
