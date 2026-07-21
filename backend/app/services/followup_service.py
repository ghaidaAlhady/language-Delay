"""Weekly follow-up: compares a new (reassessment) completion against the
child's previous completed assessment, records deterministic progress
narrative from KB04, and automatically regenerates the weekly plan.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.models.assessment import Assessment
from app.models.followup import Followup
from app.rag.schemas import Domain, ReportStatus, Severity
from app.repositories import assessment_repository, child_repository, followup_repository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.assessment import AssessmentStatus
from app.schemas.followup import FollowupResponse
from app.services.domain_priority import pick_priority_domain
from app.services.weekly_plan_service import WeeklyPlanService


def _build_next_goal(priority_domain: Domain, recommendation: str) -> str:
    return f"الهدف القادم: التركيز على مجال {priority_domain.value} — {recommendation}"


@dataclass
class FollowupService:
    session: AsyncSession
    kb: KnowledgeBaseRepository

    async def complete_followup(self, current_assessment: Assessment) -> Followup:
        if current_assessment.status != AssessmentStatus.COMPLETED:
            raise BadRequestError(
                "The assessment must be completed before creating a follow-up."
            )

        existing = await followup_repository.get_by_current_assessment_id(
            self.session, current_assessment.id
        )
        if existing is not None:
            return existing

        previous_assessment = await followup_repository.get_most_recent_completed_other_than(
            self.session,
            child_id=current_assessment.child_id,
            exclude_assessment_id=current_assessment.id,
        )
        if previous_assessment is None:
            raise BadRequestError(
                "No previous completed assessment exists for this child to compare "
                "against — this must be their first assessment, which gets a "
                "regular report instead of a follow-up."
            )

        previous_rows = await assessment_repository.get_domain_results(
            self.session, previous_assessment.id
        )
        current_rows = await assessment_repository.get_domain_results(
            self.session, current_assessment.id
        )
        previous_by_domain = {Domain(r.domain): r for r in previous_rows}
        current_by_domain = {Domain(r.domain): r for r in current_rows}

        previous_score = round(
            sum(r.score_percent for r in previous_rows) / len(previous_rows), 2
        )
        current_score = round(
            sum(r.score_percent for r in current_rows) / len(current_rows), 2
        )
        improvement = round(current_score - previous_score, 2)

        improved_domains = [
            domain
            for domain in Domain
            if current_by_domain[domain].score_percent
            > previous_by_domain[domain].score_percent
        ]
        support_needed_domains = [
            domain
            for domain in Domain
            if Severity(current_by_domain[domain].severity) != Severity.NORMAL
        ]

        # Guaranteed set together with status="completed" by
        # AssessmentService.complete(); narrows the nullable DB column.
        assert current_assessment.overall_severity is not None
        narrative_status = (
            ReportStatus.IMPROVED
            if improvement > 0
            else ReportStatus(current_assessment.overall_severity)
        )
        narrative = self.kb.get_narrative_template(narrative_status)

        priority_domain = pick_priority_domain(
            (d, Severity(row.severity), row.score_percent)
            for d, row in current_by_domain.items()
        )
        next_goal = _build_next_goal(
            priority_domain, current_by_domain[priority_domain].recommendation
        )

        followup = await followup_repository.create(
            self.session,
            child_id=current_assessment.child_id,
            previous_assessment_id=previous_assessment.id,
            current_assessment_id=current_assessment.id,
            previous_score_percent=previous_score,
            current_score_percent=current_score,
            improvement_percent=improvement,
            improved_domains=[d.value for d in improved_domains],
            support_needed_domains=[d.value for d in support_needed_domains],
            comment=narrative.text,
            next_goal=next_goal,
        )

        # generate() commits — this persists both the new followup and the
        # new weekly plan together in one transaction.
        weekly_plan_service = WeeklyPlanService(session=self.session, kb=self.kb)
        await weekly_plan_service.generate(current_assessment)

        return followup

    async def get_owned(self, *, followup_id: str, user_id: str) -> Followup:
        followup = await followup_repository.get_by_id(self.session, followup_id)
        if followup is None:
            raise NotFoundError("Follow-up not found.")
        child = await child_repository.get_by_id(self.session, followup.child_id)
        if child is None or child.user_id != user_id:
            raise NotFoundError("Follow-up not found.")
        return followup

    async def list_for_child(self, child_id: str) -> list[Followup]:
        return await followup_repository.list_for_child(self.session, child_id)

    def build_response(self, followup: Followup) -> FollowupResponse:
        return FollowupResponse(
            id=followup.id,
            child_id=followup.child_id,
            previous_assessment_id=followup.previous_assessment_id,
            current_assessment_id=followup.current_assessment_id,
            previous_score_percent=followup.previous_score_percent,
            current_score_percent=followup.current_score_percent,
            improvement_percent=followup.improvement_percent,
            improved_domains=[Domain(d) for d in followup.improved_domains],
            support_needed_domains=[Domain(d) for d in followup.support_needed_domains],
            comment=followup.comment,
            next_goal=followup.next_goal,
            created_at=followup.created_at,
        )
