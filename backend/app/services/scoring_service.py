"""Deterministic assessment scoring — no LLM involved.

Every number and recommendation produced here is derived directly from KB01,
KB03, and KB05 records, and every result carries the KB03 rule ID it came
from. This module never fabricates a score, severity, or recommendation.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.core.logging import get_logger
from app.rag.exceptions import KnowledgeBaseLookupError
from app.rag.schemas import REFERRAL_ORDER, SEVERITY_ORDER, Domain, ReferralGuidance, Severity
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.assessment import RESPONSE_WEIGHTS, ResponseValue
from app.services.domain_priority import rank_domains_by_priority

logger = get_logger(__name__)


@dataclass(frozen=True)
class DomainScoreResult:
    domain: Domain
    score_percent: float
    severity: Severity
    referral: ReferralGuidance
    decision_rule_id: str
    recommendation: str
    follow_up: str
    suggested_activity_ids: list[str]
    confidence: float


@dataclass(frozen=True)
class AssessmentScoringResult:
    domain_results: list[DomainScoreResult]
    overall_severity: Severity
    overall_referral: ReferralGuidance
    confidence_score: float
    priority_domains: list[Domain]
    strengths: list[str]
    support_needs: list[str]


def _weighted_answer_score(yes_score: float, no_score: float, weight: float) -> float:
    lower, upper = min(yes_score, no_score), max(yes_score, no_score)
    return lower + (upper - lower) * weight


def _domain_confidence(score_percent: float, low: float, high: float | None) -> float:
    """How far the score sits from the nearest band-edge ambiguity, as a
    0-1 margin. The topmost band is open-ended (no upper misclassification
    edge), so a score deep inside it — including a perfect 100% — must read
    as maximally confident rather than being penalized for nearing 100.
    """
    if high is None:
        span = 100.0 - low
        if span <= 0:
            return 1.0
        return max(0.0, min(1.0, (score_percent - low) / span))

    band_width = high - low
    if band_width <= 0:
        return 1.0
    margin = min(score_percent - low, high - score_percent)
    return max(0.0, min(1.0, margin / (band_width / 2)))


def score_assessment(
    *,
    age: int,
    answers: dict[str, ResponseValue],
    kb: KnowledgeBaseRepository,
) -> AssessmentScoringResult:
    questions = {q.id: q for q in kb.get_questions_for_age(age)}

    achieved_by_domain: dict[Domain, float] = defaultdict(float)
    max_by_domain: dict[Domain, float] = defaultdict(float)
    for question_id, response in answers.items():
        question = questions[question_id]
        weight = RESPONSE_WEIGHTS[response]
        achieved_by_domain[question.domain] += _weighted_answer_score(
            question.yes_score, question.no_score, weight
        )
        max_by_domain[question.domain] += max(question.yes_score, question.no_score)

    domain_results: list[DomainScoreResult] = []
    for domain in Domain:
        achieved = achieved_by_domain[domain]
        max_possible = max_by_domain[domain]
        score_percent = (achieved / max_possible * 100) if max_possible > 0 else 0.0

        rule = kb.get_decision_rule(age, domain, score_percent)
        low, high = kb.get_score_band(age, domain, score_percent)

        domain_results.append(
            DomainScoreResult(
                domain=domain,
                score_percent=round(score_percent, 2),
                severity=rule.severity,
                referral=rule.referral,
                decision_rule_id=rule.id,
                recommendation=rule.ai_recommendation,
                follow_up=rule.follow_up,
                suggested_activity_ids=rule.suggested_activity_ids,
                confidence=_domain_confidence(score_percent, low, high),
            )
        )

    overall_severity = max(
        (r.severity for r in domain_results), key=SEVERITY_ORDER.index
    )
    overall_referral = max(
        (r.referral for r in domain_results), key=REFERRAL_ORDER.index
    )
    confidence_score = round(
        sum(r.confidence for r in domain_results) / len(domain_results), 2
    )
    priority_domains = rank_domains_by_priority(
        (r.domain, r.severity, r.score_percent) for r in domain_results
    )

    strengths: list[str] = []
    support_needs: list[str] = []
    seen_strengths: set[str] = set()
    seen_support: set[str] = set()
    for question_id, response in answers.items():
        question = questions[question_id]
        try:
            milestone = kb.get_milestone(question.linked_milestone_id)
        except KnowledgeBaseLookupError:
            # Known KB01/KB05 data-integrity gap: KB05's linked milestone IDs
            # assume global numbering across ages, but KB01 resets IDs per
            # age sheet, so some links (mostly ages 3-5) don't resolve. This
            # only narrows the strengths/support-needs skill-name list; it
            # never affects scoring, severity, referral, or activities.
            logger.warning(
                "unresolvable_linked_milestone",
                question_id=question.id,
                linked_milestone_id=question.linked_milestone_id,
            )
            continue
        weight = RESPONSE_WEIGHTS[response]
        if weight >= 1.0:
            if milestone.skill not in seen_strengths:
                seen_strengths.add(milestone.skill)
                strengths.append(milestone.skill)
        else:
            if milestone.skill not in seen_support:
                seen_support.add(milestone.skill)
                support_needs.append(milestone.skill)

    return AssessmentScoringResult(
        domain_results=domain_results,
        overall_severity=overall_severity,
        overall_referral=overall_referral,
        confidence_score=confidence_score,
        priority_domains=priority_domains,
        strengths=strengths,
        support_needs=support_needs,
    )
