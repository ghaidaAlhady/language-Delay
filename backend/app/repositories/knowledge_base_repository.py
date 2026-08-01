"""In-memory, indexed access layer over the validated knowledge base.

Loaded once (see :func:`load_knowledge_base_repository`) and reused for the
lifetime of the process. Every lookup either returns a real, traceable KB
record or raises :class:`KnowledgeBaseLookupError` — callers must never
fabricate a substitute.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from app.rag.builder import build_knowledge_base
from app.rag.exceptions import KnowledgeBaseLookupError
from app.rag.schemas import (
    ActivityRecord,
    DecisionRuleRecord,
    Domain,
    KnowledgeBase,
    MilestoneRecord,
    NarrativeTemplate,
    QuestionRecord,
    ReferenceRecord,
    ReportStatus,
    WeeklyFollowupQuestionRecord,
)


@dataclass(frozen=True)
class _DecisionRuleBand:
    rule: DecisionRuleRecord
    low_inclusive: float
    high_exclusive: float | None


@dataclass(frozen=True)
class SelectedWeeklyFollowupQuestion:
    """A KB06 template deterministically bound to one approved KB02 activity."""

    id: str
    source_record: WeeklyFollowupQuestionRecord
    activity: ActivityRecord
    question_text_ar: str
    fallback_used: bool


@dataclass
class KnowledgeBaseRepository:
    kb: KnowledgeBase

    _milestones_by_id: dict[str, MilestoneRecord] = field(init=False, default_factory=dict)
    _activities_by_id: dict[str, ActivityRecord] = field(init=False, default_factory=dict)
    _decision_rules_by_id: dict[str, DecisionRuleRecord] = field(
        init=False, default_factory=dict
    )
    _questions_by_age: dict[int, list[QuestionRecord]] = field(init=False, default_factory=dict)
    _activities_by_age_domain: dict[tuple[int, Domain], list[ActivityRecord]] = field(
        init=False, default_factory=dict
    )
    _decision_bands: dict[tuple[int, Domain], list[_DecisionRuleBand]] = field(
        init=False, default_factory=dict
    )
    _narrative_by_status: dict[ReportStatus, NarrativeTemplate] = field(
        init=False, default_factory=dict
    )
    _reference_by_code: dict[str, ReferenceRecord] = field(init=False, default_factory=dict)
    _weekly_followup_questions: list[WeeklyFollowupQuestionRecord] = field(
        init=False, default_factory=list
    )

    def __post_init__(self) -> None:
        self._milestones_by_id = {m.id: m for m in self.kb.milestones}
        self._activities_by_id = {a.id: a for a in self.kb.activities}
        self._decision_rules_by_id = {r.id: r for r in self.kb.decision_rules}
        self._reference_by_code = {r.code: r for r in self.kb.references}
        self._weekly_followup_questions = sorted(
            (q for q in self.kb.weekly_followup_questions if q.active),
            key=lambda q: q.id,
        )

        questions_by_age: dict[int, list[QuestionRecord]] = defaultdict(list)
        for question in self.kb.questions:
            questions_by_age[question.age].append(question)
        self._questions_by_age = {
            age: sorted(qs, key=lambda q: q.id) for age, qs in questions_by_age.items()
        }

        activities_by_age_domain: dict[tuple[int, Domain], list[ActivityRecord]] = defaultdict(list)
        for activity in self.kb.activities:
            activities_by_age_domain[(activity.age, activity.domain)].append(activity)
        self._activities_by_age_domain = dict(activities_by_age_domain)

        narrative_by_status: dict[ReportStatus, NarrativeTemplate] = {}
        for template in self.kb.narrative_templates:
            narrative_by_status[template.status] = template
        self._narrative_by_status = narrative_by_status

        rules_by_age_domain: dict[tuple[int, Domain], list[DecisionRuleRecord]] = defaultdict(list)
        for rule in self.kb.decision_rules:
            rules_by_age_domain[(rule.age, rule.domain)].append(rule)

        self._decision_bands = {
            key: self._build_bands(rules) for key, rules in rules_by_age_domain.items()
        }

    @staticmethod
    def _build_bands(rules: list[DecisionRuleRecord]) -> list[_DecisionRuleBand]:
        ordered = sorted(rules, key=lambda r: r.score_threshold)
        bands: list[_DecisionRuleBand] = []
        for index, rule in enumerate(ordered):
            high = ordered[index + 1].score_threshold if index + 1 < len(ordered) else None
            bands.append(
                _DecisionRuleBand(
                    rule=rule, low_inclusive=rule.score_threshold, high_exclusive=high
                )
            )
        return bands

    # -- Milestones (KB01) --------------------------------------------------

    def get_milestone(self, milestone_id: str) -> MilestoneRecord:
        try:
            return self._milestones_by_id[milestone_id]
        except KeyError as exc:
            raise KnowledgeBaseLookupError(f"Unknown milestone ID: {milestone_id!r}") from exc

    def get_milestones_for_age(
        self, age: int, domain: Domain | None = None
    ) -> list[MilestoneRecord]:
        results = [m for m in self.kb.milestones if m.age == age]
        if domain is not None:
            results = [m for m in results if m.domain == domain]
        return results

    def get_reference(self, code: str) -> ReferenceRecord | None:
        return self._reference_by_code.get(code)

    @property
    def references(self) -> list[ReferenceRecord]:
        return self.kb.references

    # -- Activities (KB02) ----------------------------------------------------

    def get_activity(self, activity_id: str) -> ActivityRecord:
        try:
            return self._activities_by_id[activity_id]
        except KeyError as exc:
            raise KnowledgeBaseLookupError(f"Unknown activity ID: {activity_id!r}") from exc

    def get_activities_by_ids(self, activity_ids: list[str]) -> list[ActivityRecord]:
        return [self.get_activity(activity_id) for activity_id in activity_ids]

    def get_activities_for_age(
        self, age: int, domain: Domain | None = None
    ) -> list[ActivityRecord]:
        if domain is not None:
            return list(self._activities_by_age_domain.get((age, domain), []))
        return [a for a in self.kb.activities if a.age == age]

    # -- Decision rules (KB03) ------------------------------------------------

    def get_decision_rule_by_id(self, rule_id: str) -> DecisionRuleRecord:
        try:
            return self._decision_rules_by_id[rule_id]
        except KeyError as exc:
            raise KnowledgeBaseLookupError(
                f"Unknown decision rule ID: {rule_id!r}"
            ) from exc

    def _find_band(self, age: int, domain: Domain, score_percent: float) -> _DecisionRuleBand:
        bands = self._decision_bands.get((age, domain))
        if not bands:
            raise KnowledgeBaseLookupError(
                f"No decision rules for age={age}, domain={domain.value!r}"
            )

        for band in bands:
            if band.high_exclusive is None:
                if score_percent >= band.low_inclusive:
                    return band
            elif band.low_inclusive <= score_percent < band.high_exclusive:
                return band

        raise KnowledgeBaseLookupError(
            f"No decision rule band covers score={score_percent} for "
            f"age={age}, domain={domain.value!r}"
        )

    def get_decision_rule(
        self, age: int, domain: Domain, score_percent: float
    ) -> DecisionRuleRecord:
        return self._find_band(age, domain, score_percent).rule

    def get_score_band(
        self, age: int, domain: Domain, score_percent: float
    ) -> tuple[float, float | None]:
        """Return the ``(low_inclusive, high_exclusive)`` band a score falls
        into, for confidence-margin calculations. ``high_exclusive is None``
        means the top (unbounded) band.
        """
        band = self._find_band(age, domain, score_percent)
        return band.low_inclusive, band.high_exclusive

    # -- Assessment questions (KB05) -------------------------------------------

    def get_questions_for_age(self, age: int) -> list[QuestionRecord]:
        return list(self._questions_by_age.get(age, []))

    # -- Weekly follow-up questions (KB06) ------------------------------------

    def select_weekly_followup_questions(
        self, *, age: int, activities: list[ActivityRecord]
    ) -> list[SelectedWeeklyFollowupQuestion]:
        """Bind 5-8 KB06 templates to the plan's real KB02 activities.

        Exact activity/domain templates always win. The generic templates are
        used only for an activity that has no eligible specific KB06 record.
        """
        selected: list[SelectedWeeklyFollowupQuestion] = []
        for index, activity in enumerate(activities[:8]):
            eligible = [
                question
                for question in self._weekly_followup_questions
                if question.age_min <= age <= question.age_max
                and not question.is_generic_fallback
                and question.domain == activity.domain
                and activity.id in question.applicable_activity_ids
            ]
            fallback_used = False
            if not eligible:
                eligible = [
                    question
                    for question in self._weekly_followup_questions
                    if question.age_min <= age <= question.age_max
                    and question.is_generic_fallback
                    and (question.domain is None or question.domain == activity.domain)
                ]
                fallback_used = True
            if not eligible:
                raise KnowledgeBaseLookupError(
                    f"No KB06 question covers age={age}, activity={activity.id!r}"
                )

            template = eligible[index % len(eligible)]
            question_id = f"{template.id}-{activity.id}"
            if len(question_id) > 20:
                raise KnowledgeBaseLookupError(
                    f"Generated KB06 question ID exceeds storage limit: {question_id!r}"
                )
            selected.append(
                SelectedWeeklyFollowupQuestion(
                    id=question_id,
                    source_record=template,
                    activity=activity,
                    question_text_ar=template.question_text_ar.format(
                        activity=activity.name,
                        skill=activity.target_skill,
                        goal=activity.goal,
                        domain=activity.domain.value,
                        expected_behavior=activity.expected_outcome,
                    ),
                    fallback_used=fallback_used,
                )
            )

        if len(selected) < 5:
            raise KnowledgeBaseLookupError(
                "A weekly plan must provide at least five activities for KB06 selection."
            )
        return selected

    # -- Report templates (KB04) ------------------------------------------------

    def get_narrative_template(self, status: ReportStatus) -> NarrativeTemplate:
        try:
            return self._narrative_by_status[status]
        except KeyError as exc:
            raise KnowledgeBaseLookupError(
                f"No narrative template for status: {status.value!r}"
            ) from exc

    @property
    def initial_report_fields(self) -> list:
        return self.kb.initial_report_fields

    @property
    def progress_report_fields(self) -> list:
        return self.kb.progress_report_fields

    @property
    def referral_report_fields(self) -> list:
        return self.kb.referral_report_fields

    @property
    def weekly_plan_template(self) -> list:
        return self.kb.weekly_plan_template


def load_knowledge_base_repository(kb_dir: Path) -> KnowledgeBaseRepository:
    """Load and validate KB01-KB06 from ``kb_dir`` and build the repository.

    Intended to run once at application startup; failures are structural data
    problems and should fail fast rather than be caught per-request.
    """
    return KnowledgeBaseRepository(kb=build_knowledge_base(kb_dir))
