"""Assessment lifecycle: start, question retrieval, answer submission,
completion (scoring), and result/history retrieval — all ownership-scoped.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import utcnow
from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.models.assessment import Assessment
from app.models.child import Child
from app.rag.schemas import Domain, QuestionRecord, ReferralGuidance, Severity
from app.repositories import assessment_repository, child_repository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.assessment import (
    RESPONSE_WEIGHTS,
    AnswerSubmissionRequest,
    AssessmentDomainResultResponse,
    AssessmentResponse,
    AssessmentStatus,
    ResponseValue,
)
from app.services.age_service import (
    MAX_ASSESSMENT_AGE,
    MIN_ASSESSMENT_AGE,
    compute_age_years,
    is_assessment_age_eligible,
)
from app.services.scoring_service import score_assessment


@dataclass
class AssessmentService:
    session: AsyncSession
    kb: KnowledgeBaseRepository

    async def start(self, child: Child) -> Assessment:
        age = compute_age_years(child.date_of_birth)
        if not is_assessment_age_eligible(age):
            raise BadRequestError(
                f"Child's current age ({age}) is outside the supported assessment "
                f"range ({MIN_ASSESSMENT_AGE}-{MAX_ASSESSMENT_AGE} years)."
            )
        assessment = await assessment_repository.create(
            self.session, child_id=child.id, age_at_assessment=age
        )
        await self.session.commit()
        return assessment

    async def list_for_child(self, child_id: str) -> list[Assessment]:
        return await assessment_repository.list_for_child(self.session, child_id)

    async def get_owned(self, *, assessment_id: str, user_id: str) -> Assessment:
        assessment = await assessment_repository.get_by_id(self.session, assessment_id)
        if assessment is None:
            raise NotFoundError("Assessment not found.")
        child = await child_repository.get_by_id(self.session, assessment.child_id)
        if child is None or child.user_id != user_id:
            # Same response for "missing" and "belongs to someone else".
            raise NotFoundError("Assessment not found.")
        return assessment

    def get_questions(self, assessment: Assessment) -> list[QuestionRecord]:
        return self.kb.get_questions_for_age(assessment.age_at_assessment)

    async def get_recommended_activity_ids(self, assessment: Assessment) -> list[str]:
        domain_rows = await assessment_repository.get_domain_results(
            self.session, assessment.id
        )
        activity_ids: list[str] = []
        seen: set[str] = set()
        for row in domain_rows:
            for activity_id in row.suggested_activity_ids:
                if activity_id not in seen:
                    seen.add(activity_id)
                    activity_ids.append(activity_id)
        return activity_ids

    async def submit_answers(
        self, assessment: Assessment, payload: AnswerSubmissionRequest
    ) -> Assessment:
        if assessment.status != AssessmentStatus.IN_PROGRESS:
            raise ConflictError("This assessment has already been completed.")

        valid_question_ids = {q.id for q in self.get_questions(assessment)}
        unknown_ids = sorted(
            {item.question_id for item in payload.answers} - valid_question_ids
        )
        if unknown_ids:
            raise BadRequestError(
                "One or more question IDs are not valid for this assessment's age.",
                details={"invalid_question_ids": unknown_ids},
            )

        for item in payload.answers:
            await assessment_repository.upsert_answer(
                self.session,
                assessment_id=assessment.id,
                question_id=item.question_id,
                response=item.response.value,
                score_weight=RESPONSE_WEIGHTS[item.response],
            )
        await self.session.commit()
        return assessment

    async def complete(self, assessment: Assessment) -> Assessment:
        if assessment.status != AssessmentStatus.IN_PROGRESS:
            raise ConflictError("This assessment has already been completed.")

        questions = self.get_questions(assessment)
        answers = await assessment_repository.get_answers(self.session, assessment.id)
        answered_ids = {a.question_id for a in answers}
        missing = sorted(q.id for q in questions if q.id not in answered_ids)
        if missing:
            raise BadRequestError(
                "All questions must be answered before completing the assessment.",
                details={"missing_question_ids": missing},
            )

        answer_map = {a.question_id: ResponseValue(a.response) for a in answers}
        result = score_assessment(
            age=assessment.age_at_assessment, answers=answer_map, kb=self.kb
        )

        await assessment_repository.save_domain_results(
            self.session, assessment_id=assessment.id, results=result.domain_results
        )
        await assessment_repository.mark_completed(
            self.session,
            assessment,
            overall_severity=result.overall_severity.value,
            overall_referral=result.overall_referral.value,
            confidence_score=result.confidence_score,
            completed_at=utcnow(),
        )
        await self.session.commit()
        return assessment

    async def build_response(self, assessment: Assessment) -> AssessmentResponse:
        questions = self.get_questions(assessment)
        answers = await assessment_repository.get_answers(self.session, assessment.id)
        domain_rows = await assessment_repository.get_domain_results(
            self.session, assessment.id
        )

        domain_results = [
            AssessmentDomainResultResponse(
                domain=Domain(row.domain),
                score_percent=row.score_percent,
                severity=Severity(row.severity),
                referral=ReferralGuidance(row.referral),
                decision_rule_id=row.decision_rule_id,
                recommendation=row.recommendation,
                follow_up=row.follow_up,
                suggested_activity_ids=row.suggested_activity_ids,
            )
            for row in domain_rows
        ]

        priority_domains: list[Domain] = []
        strengths: list[str] = []
        support_needs: list[str] = []
        if assessment.status == AssessmentStatus.COMPLETED:
            answer_map = {a.question_id: ResponseValue(a.response) for a in answers}
            fresh = score_assessment(
                age=assessment.age_at_assessment, answers=answer_map, kb=self.kb
            )
            priority_domains = fresh.priority_domains
            strengths = fresh.strengths
            support_needs = fresh.support_needs

        return AssessmentResponse(
            id=assessment.id,
            child_id=assessment.child_id,
            age_at_assessment=assessment.age_at_assessment,
            status=AssessmentStatus(assessment.status),
            started_at=assessment.created_at,
            completed_at=assessment.completed_at,
            answered_count=len(answers),
            total_questions=len(questions),
            overall_severity=(
                Severity(assessment.overall_severity) if assessment.overall_severity else None
            ),
            overall_referral=(
                ReferralGuidance(assessment.overall_referral)
                if assessment.overall_referral
                else None
            ),
            confidence_score=assessment.confidence_score,
            priority_domains=priority_domains,
            strengths=strengths,
            support_needs=support_needs,
            domain_results=domain_results,
        )
