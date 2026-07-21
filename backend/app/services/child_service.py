"""Child profile management, scoped to the owning parent."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.child import Child
from app.repositories import child_repository
from app.schemas.child import ChildCreateRequest, ChildResponse, ChildUpdateRequest
from app.services.age_service import compute_age_years, is_assessment_age_eligible


def build_child_response(child: Child) -> ChildResponse:
    age_years = compute_age_years(child.date_of_birth)
    return ChildResponse(
        id=child.id,
        name=child.name,
        date_of_birth=child.date_of_birth,
        gender=child.gender,
        home_language=child.home_language,
        has_previous_diagnosis=child.has_previous_diagnosis,
        previous_diagnosis_details=child.previous_diagnosis_details,
        has_hearing_problems=child.has_hearing_problems,
        uses_hearing_aid=child.uses_hearing_aid,
        notes=child.notes,
        age_years=age_years,
        is_assessment_age_eligible=is_assessment_age_eligible(age_years),
        created_at=child.created_at,
        updated_at=child.updated_at,
    )


@dataclass
class ChildService:
    session: AsyncSession

    async def create(self, *, user_id: str, payload: ChildCreateRequest) -> Child:
        child = await child_repository.create(
            self.session,
            user_id=user_id,
            name=payload.name,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender.value,
            home_language=payload.home_language,
            has_previous_diagnosis=payload.has_previous_diagnosis,
            previous_diagnosis_details=payload.previous_diagnosis_details,
            has_hearing_problems=payload.has_hearing_problems,
            uses_hearing_aid=payload.uses_hearing_aid,
            notes=payload.notes,
        )
        await self.session.commit()
        return child

    async def list_for_user(self, user_id: str) -> list[Child]:
        return await child_repository.list_for_user(self.session, user_id)

    async def get_owned(self, *, child_id: str, user_id: str) -> Child:
        child = await child_repository.get_by_id(self.session, child_id)
        if child is None or child.user_id != user_id:
            # Same response for "missing" and "belongs to someone else" so
            # existence of another parent's child is never revealed.
            raise NotFoundError("Child not found.")
        return child

    async def update(self, *, child: Child, payload: ChildUpdateRequest) -> Child:
        updates = payload.model_dump(exclude_unset=True)
        if "gender" in updates:
            updates["gender"] = updates["gender"].value
        for field_name, value in updates.items():
            setattr(child, field_name, value)
        await self.session.commit()
        return child

    async def delete(self, child: Child) -> None:
        await child_repository.delete(self.session, child)
        await self.session.commit()
