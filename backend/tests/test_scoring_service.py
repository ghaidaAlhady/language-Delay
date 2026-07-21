from __future__ import annotations

from app.rag.schemas import Domain, ReferralGuidance, Severity
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.assessment import ResponseValue
from app.services.scoring_service import score_assessment


def _answers_for_age(
    kb_repository: KnowledgeBaseRepository, age: int, response: ResponseValue
) -> dict[str, ResponseValue]:
    return {q.id: response for q in kb_repository.get_questions_for_age(age)}


def test_all_always_scores_every_domain_100_and_normal(
    kb_repository: KnowledgeBaseRepository,
) -> None:
    answers = _answers_for_age(kb_repository, 2, ResponseValue.ALWAYS)
    result = score_assessment(age=2, answers=answers, kb=kb_repository)

    assert len(result.domain_results) == 4
    for domain_result in result.domain_results:
        assert domain_result.score_percent == 100.0
        assert domain_result.severity == Severity.NORMAL
        assert domain_result.referral == ReferralGuidance.NO

    assert result.overall_severity == Severity.NORMAL
    assert result.overall_referral == ReferralGuidance.NO
    assert result.support_needs == []
    assert len(result.strengths) == 20


def test_all_never_scores_every_domain_0_and_notable(
    kb_repository: KnowledgeBaseRepository,
) -> None:
    answers = _answers_for_age(kb_repository, 2, ResponseValue.NEVER)
    result = score_assessment(age=2, answers=answers, kb=kb_repository)

    for domain_result in result.domain_results:
        assert domain_result.score_percent == 0.0
        assert domain_result.severity == Severity.NOTABLE_DELAY
        assert domain_result.referral == ReferralGuidance.YES
        assert domain_result.suggested_activity_ids  # traceable to real KB02 IDs

    assert result.overall_severity == Severity.NOTABLE_DELAY
    assert result.overall_referral == ReferralGuidance.YES
    assert result.strengths == []
    assert len(result.support_needs) == 20


def test_one_weak_domain_drives_overall_result(kb_repository: KnowledgeBaseRepository) -> None:
    answers = _answers_for_age(kb_repository, 2, ResponseValue.ALWAYS)
    speech_questions = [
        q for q in kb_repository.get_questions_for_age(2) if q.domain == Domain.SPEECH
    ]
    # 4/5 always (full credit) + 1/5 never (no credit) = 80% -> mild delay band.
    answers[speech_questions[0].id] = ResponseValue.NEVER

    result = score_assessment(age=2, answers=answers, kb=kb_repository)

    by_domain = {r.domain: r for r in result.domain_results}
    assert by_domain[Domain.SPEECH].score_percent == 80.0
    assert by_domain[Domain.SPEECH].severity == Severity.MILD_DELAY
    assert by_domain[Domain.SPEECH].referral == ReferralGuidance.NO
    assert by_domain[Domain.RECEPTIVE_LANGUAGE].severity == Severity.NORMAL

    # Overall = worst domain present (mild beats normal).
    assert result.overall_severity == Severity.MILD_DELAY
    assert result.priority_domains[0] == Domain.SPEECH


def test_sometimes_gives_half_credit(kb_repository: KnowledgeBaseRepository) -> None:
    answers = _answers_for_age(kb_repository, 3, ResponseValue.SOMETIMES)
    result = score_assessment(age=3, answers=answers, kb=kb_repository)
    for domain_result in result.domain_results:
        assert domain_result.score_percent == 50.0
        assert domain_result.severity == Severity.MODERATE_DELAY
        assert domain_result.referral == ReferralGuidance.CONSIDER


def test_every_domain_result_traces_to_a_real_decision_rule(
    kb_repository: KnowledgeBaseRepository,
) -> None:
    answers = _answers_for_age(kb_repository, 4, ResponseValue.OFTEN)
    result = score_assessment(age=4, answers=answers, kb=kb_repository)
    for domain_result in result.domain_results:
        rule = kb_repository.get_decision_rule(4, domain_result.domain, domain_result.score_percent)
        assert rule.id == domain_result.decision_rule_id
        assert rule.ai_recommendation == domain_result.recommendation


def test_scoring_survives_unresolvable_kb01_milestone_links(
    kb_repository: KnowledgeBaseRepository,
) -> None:
    """KB05's linked_milestone_id assumes global numbering across ages, but
    KB01 resets milestone IDs per age sheet, so most ages-3-5 links don't
    resolve (see docs/DECISIONS_AND_ASSUMPTIONS.md). Scoring, severity,
    referral, and activities must stay fully correct regardless; only the
    strengths/support-needs skill-name list may come back shorter than 20.
    """
    answers = _answers_for_age(kb_repository, 5, ResponseValue.ALWAYS)
    result = score_assessment(age=5, answers=answers, kb=kb_repository)

    for domain_result in result.domain_results:
        assert domain_result.score_percent == 100.0
        assert domain_result.severity == Severity.NORMAL
        assert domain_result.suggested_activity_ids

    assert len(result.strengths) <= 20
    assert result.support_needs == []


def test_confidence_score_is_between_zero_and_one(kb_repository: KnowledgeBaseRepository) -> None:
    answers = _answers_for_age(kb_repository, 5, ResponseValue.RARELY)
    result = score_assessment(age=5, answers=answers, kb=kb_repository)
    assert 0.0 <= result.confidence_score <= 1.0


def test_confidence_is_low_near_a_band_boundary_and_high_at_band_center(
    kb_repository: KnowledgeBaseRepository,
) -> None:
    # 50% sits exactly on the moderate/notable boundary -> minimal confidence.
    boundary_answers = _answers_for_age(kb_repository, 2, ResponseValue.SOMETIMES)
    boundary_result = score_assessment(age=2, answers=boundary_answers, kb=kb_repository)

    # 100% sits at the center-ish of the open-ended normal band -> high confidence.
    centered_answers = _answers_for_age(kb_repository, 2, ResponseValue.ALWAYS)
    centered_result = score_assessment(age=2, answers=centered_answers, kb=kb_repository)

    assert boundary_result.confidence_score < centered_result.confidence_score
