"""Deterministic Arabic report generation from a completed assessment.

Every sentence in a generated report comes from a KB04 narrative template
(keyed by the assessment's overall severity) or is assembled from KB03
recommendation/follow-up text — nothing is written by an LLM, and nothing is
fabricated. If no external LLM provider is configured (the default), this is
the *only* report-generation path; see app/core/config.py::llm_configured.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DISCLAIMER_AR, WEEKLY_REASSESSMENT_AR
from app.core.errors import BadRequestError, NotFoundError
from app.models.assessment import Assessment
from app.models.report import Report
from app.rag.schemas import Domain, ReferralGuidance, ReportStatus, Severity
from app.repositories import assessment_repository, child_repository, report_repository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.assessment import AssessmentStatus
from app.schemas.report import ReportDomainSummary, ReportResponse
from app.services.age_service import compute_age_years
from app.services.assessment_service import AssessmentService
from app.services.domain_priority import pick_priority_domain


def _build_weekly_goal(priority_domain: Domain, recommendation: str) -> str:
    return f"التركيز هذا الأسبوع على مجال {priority_domain.value}: {recommendation}"


@dataclass
class ReportService:
    session: AsyncSession
    kb: KnowledgeBaseRepository

    async def generate(self, assessment: Assessment) -> Report:
        if assessment.status != AssessmentStatus.COMPLETED:
            raise BadRequestError("The assessment must be completed before generating a report.")

        existing = await report_repository.get_by_assessment_id(self.session, assessment.id)
        if existing is not None:
            return existing

        domain_rows = await assessment_repository.get_domain_results(
            self.session, assessment.id
        )
        by_domain = {Domain(row.domain): row for row in domain_rows}
        priority_domain = pick_priority_domain(
            (d, Severity(row.severity), row.score_percent) for d, row in by_domain.items()
        )
        priority_row = by_domain[priority_domain]

        # Guaranteed set together with status="completed" by
        # AssessmentService.complete(); narrows the nullable DB column for
        # the type checker.
        assert assessment.overall_severity is not None
        narrative = self.kb.get_narrative_template(ReportStatus(assessment.overall_severity))

        report_number = await report_repository.next_report_number(self.session)
        report = await report_repository.create(
            self.session,
            assessment_id=assessment.id,
            report_number=report_number,
            summary_text=narrative.text,
            weekly_goal=_build_weekly_goal(priority_domain, priority_row.recommendation),
            next_reassessment=WEEKLY_REASSESSMENT_AR,
        )
        await self.session.commit()
        return report

    async def get_owned(self, *, report_id: str, user_id: str) -> Report:
        report = await report_repository.get_by_id(self.session, report_id)
        if report is None:
            raise NotFoundError("Report not found.")
        assessment = await assessment_repository.get_by_id(self.session, report.assessment_id)
        if assessment is None:
            raise NotFoundError("Report not found.")
        child = await child_repository.get_by_id(self.session, assessment.child_id)
        if child is None or child.user_id != user_id:
            raise NotFoundError("Report not found.")
        return report

    async def list_for_child(self, child_id: str) -> list[Report]:
        return await report_repository.list_for_child(self.session, child_id)

    async def build_response(self, report: Report) -> ReportResponse:
        assessment = await assessment_repository.get_by_id(self.session, report.assessment_id)
        if assessment is None:
            raise NotFoundError("Report not found.")
        child = await child_repository.get_by_id(self.session, assessment.child_id)
        if child is None:
            raise NotFoundError("Report not found.")

        domain_rows = await assessment_repository.get_domain_results(
            self.session, assessment.id
        )
        domain_summaries = [
            ReportDomainSummary(
                domain=Domain(row.domain),
                score_percent=row.score_percent,
                severity=Severity(row.severity),
                recommendation=row.recommendation,
            )
            for row in domain_rows
        ]

        assessment_service = AssessmentService(session=self.session, kb=self.kb)
        recommended_activity_ids = await assessment_service.get_recommended_activity_ids(
            assessment
        )
        assessment_response = await assessment_service.build_response(assessment)

        # A Report only ever exists for a completed assessment (see
        # generate()), so these are guaranteed set; narrows the nullable DB
        # columns for the type checker.
        assert assessment.overall_severity is not None
        assert assessment.overall_referral is not None
        overall_referral = ReferralGuidance(assessment.overall_referral)
        return ReportResponse(
            id=report.id,
            report_number=report.report_number,
            language=report.language,
            child_id=child.id,
            child_name=child.name,
            child_age_years=compute_age_years(child.date_of_birth),
            assessment_id=assessment.id,
            generated_at=report.created_at,
            overall_severity=Severity(assessment.overall_severity),
            overall_referral=overall_referral,
            referral_recommended=overall_referral != ReferralGuidance.NO,
            confidence_score=assessment.confidence_score or 0.0,
            domain_summaries=domain_summaries,
            strengths=assessment_response.strengths,
            support_needs=assessment_response.support_needs,
            summary_text=report.summary_text,
            weekly_goal=report.weekly_goal,
            recommended_activity_ids=recommended_activity_ids,
            # Existing persisted reports may contain older KB03 timing (for
            # example, four weeks or three months). The parent workflow is
            # weekly, so every user-facing report response is normalized.
            next_reassessment=WEEKLY_REASSESSMENT_AR,
            disclaimer=DISCLAIMER_AR,
        )
