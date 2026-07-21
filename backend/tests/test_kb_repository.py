from __future__ import annotations

import pytest

from app.rag.exceptions import KnowledgeBaseLookupError
from app.rag.schemas import Domain, ReferralGuidance, ReportStatus, Severity
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository


def test_questions_for_age_cover_all_domains(kb_repository: KnowledgeBaseRepository) -> None:
    for age in (2, 3, 4, 5):
        questions = kb_repository.get_questions_for_age(age)
        assert len(questions) == 20
        domains = {q.domain for q in questions}
        assert domains == set(Domain)


def test_questions_for_unknown_age_returns_empty(kb_repository: KnowledgeBaseRepository) -> None:
    assert kb_repository.get_questions_for_age(6) == []


def test_milestones_for_age_and_domain(kb_repository: KnowledgeBaseRepository) -> None:
    milestones = kb_repository.get_milestones_for_age(2, Domain.RECEPTIVE_LANGUAGE)
    assert len(milestones) > 0
    assert all(m.age == 2 and m.domain == Domain.RECEPTIVE_LANGUAGE for m in milestones)
    assert all(m.source_file == "KB01.xlsx" for m in milestones)


def test_get_activity_by_id_traceable(kb_repository: KnowledgeBaseRepository) -> None:
    activity = kb_repository.get_activity("A001")
    assert activity.source_file == "KB02.xlsx"
    assert activity.source_sheet == "Activities"


def test_get_unknown_activity_raises(kb_repository: KnowledgeBaseRepository) -> None:
    with pytest.raises(KnowledgeBaseLookupError):
        kb_repository.get_activity("A999")


def test_get_activities_by_ids_preserves_order(kb_repository: KnowledgeBaseRepository) -> None:
    activities = kb_repository.get_activities_by_ids(["A002", "A001"])
    assert [a.id for a in activities] == ["A002", "A001"]


@pytest.mark.parametrize(
    ("score", "expected_severity", "expected_referral"),
    [
        (100.0, Severity.NORMAL, ReferralGuidance.NO),
        (85.0, Severity.NORMAL, ReferralGuidance.NO),
        (84.999, Severity.MILD_DELAY, ReferralGuidance.NO),
        (70.0, Severity.MILD_DELAY, ReferralGuidance.NO),
        (69.999, Severity.MODERATE_DELAY, ReferralGuidance.CONSIDER),
        (50.0, Severity.MODERATE_DELAY, ReferralGuidance.CONSIDER),
        (49.999, Severity.NOTABLE_DELAY, ReferralGuidance.YES),
        (0.0, Severity.NOTABLE_DELAY, ReferralGuidance.YES),
    ],
)
def test_decision_rule_bands_partition_score_range(
    kb_repository: KnowledgeBaseRepository,
    score: float,
    expected_severity: Severity,
    expected_referral: ReferralGuidance,
) -> None:
    rule = kb_repository.get_decision_rule(2, Domain.RECEPTIVE_LANGUAGE, score)
    assert rule.severity == expected_severity
    assert rule.referral == expected_referral


def test_decision_rule_unknown_age_domain_raises(kb_repository: KnowledgeBaseRepository) -> None:
    with pytest.raises(KnowledgeBaseLookupError):
        kb_repository.get_decision_rule(6, Domain.RECEPTIVE_LANGUAGE, 90)


def test_decision_rule_activities_resolve_to_real_records(
    kb_repository: KnowledgeBaseRepository,
) -> None:
    rule = kb_repository.get_decision_rule(2, Domain.SPEECH, 10)
    activities = kb_repository.get_activities_by_ids(rule.suggested_activity_ids)
    assert len(activities) == len(rule.suggested_activity_ids)
    assert all(a.domain == Domain.SPEECH and a.age == 2 for a in activities)


def test_narrative_templates_cover_all_statuses(kb_repository: KnowledgeBaseRepository) -> None:
    for status in ReportStatus:
        template = kb_repository.get_narrative_template(status)
        assert template.text
        assert template.source_file == "KB04.xlsx"


def test_reference_lookup(kb_repository: KnowledgeBaseRepository) -> None:
    reference = kb_repository.get_reference("ASHA")
    assert reference is not None
    assert reference.description


def test_reference_lookup_unknown_returns_none(kb_repository: KnowledgeBaseRepository) -> None:
    assert kb_repository.get_reference("NOT_A_REAL_REFERENCE") is None
