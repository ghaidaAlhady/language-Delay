from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import utcnow
from app.core.errors import NotFoundError
from app.models.child import Child
from app.repositories import user_repository
from app.schemas.child import ChildCreateRequest, ChildUpdateRequest, Gender
from app.services.auth_service import AuthService
from app.services.child_service import ChildService, build_child_response

MakeUser = Callable[..., Awaitable[str]]


@pytest.fixture
def child_service(db_session: AsyncSession) -> ChildService:
    return ChildService(session=db_session)


@pytest_asyncio.fixture
async def make_user(db_session: AsyncSession) -> MakeUser:
    """Factory for real, FK-satisfying users; returns the new user's ID."""

    async def _make_user(email: str = "parent@example.com") -> str:
        user = await user_repository.create(
            db_session, email=email, hashed_password="x", display_name="Parent"
        )
        await db_session.commit()
        return user.id

    return _make_user


def _create_payload(**overrides: object) -> ChildCreateRequest:
    defaults: dict[str, object] = {
        "name": "Layla",
        "date_of_birth": date(2023, 1, 1),
        "gender": Gender.FEMALE,
        "home_language": "ar",
    }
    defaults.update(overrides)
    return ChildCreateRequest(**defaults)


async def test_create_child(child_service: ChildService, make_user: MakeUser) -> None:
    user_id = await make_user()
    child = await child_service.create(user_id=user_id, payload=_create_payload())
    assert child.id
    assert child.name == "Layla"
    assert child.user_id == user_id


async def test_list_for_user_only_returns_owned_children(
    child_service: ChildService, make_user: MakeUser
) -> None:
    user_a = await make_user("a@example.com")
    user_b = await make_user("b@example.com")
    await child_service.create(user_id=user_a, payload=_create_payload(name="A"))
    await child_service.create(user_id=user_b, payload=_create_payload(name="B"))

    children = await child_service.list_for_user(user_a)
    assert [c.name for c in children] == ["A"]


async def test_get_owned_raises_not_found_for_other_users_child(
    child_service: ChildService, make_user: MakeUser
) -> None:
    user_a = await make_user("a@example.com")
    user_b = await make_user("b@example.com")
    child = await child_service.create(user_id=user_a, payload=_create_payload())
    with pytest.raises(NotFoundError):
        await child_service.get_owned(child_id=child.id, user_id=user_b)


async def test_get_owned_raises_not_found_for_missing_child(
    child_service: ChildService, make_user: MakeUser
) -> None:
    user_id = await make_user()
    with pytest.raises(NotFoundError):
        await child_service.get_owned(child_id="does-not-exist", user_id=user_id)


async def test_update_applies_partial_changes(
    child_service: ChildService, make_user: MakeUser
) -> None:
    user_id = await make_user()
    child = await child_service.create(user_id=user_id, payload=_create_payload())
    updated = await child_service.update(
        child=child, payload=ChildUpdateRequest(name="New Name")
    )
    assert updated.name == "New Name"
    assert updated.home_language == "ar"  # unchanged


async def test_delete_removes_child(
    child_service: ChildService, make_user: MakeUser
) -> None:
    user_id = await make_user()
    child = await child_service.create(user_id=user_id, payload=_create_payload())
    await child_service.delete(child)
    with pytest.raises(NotFoundError):
        await child_service.get_owned(child_id=child.id, user_id=user_id)


def test_build_child_response_computes_age() -> None:
    # Column defaults only apply on INSERT, so set booleans explicitly here
    # rather than relying on ORM-level defaults for this in-memory object.
    child = Child(
        id="c1",
        user_id="u1",
        name="Layla",
        date_of_birth=date.today().replace(year=date.today().year - 3),
        gender="female",
        home_language="ar",
        has_previous_diagnosis=False,
        has_hearing_problems=False,
        uses_hearing_aid=False,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    response = build_child_response(child)
    assert response.age_years == 3
    assert response.is_assessment_age_eligible is True


async def test_account_deletion_cascades_to_children(
    db_session: AsyncSession, settings: Settings
) -> None:
    auth_service = AuthService(session=db_session, settings=settings)
    user = await user_repository.create(
        db_session, email="parent@example.com", hashed_password="x", display_name="P"
    )
    await db_session.commit()

    child_service = ChildService(session=db_session)
    await child_service.create(user_id=user.id, payload=_create_payload())

    await auth_service.delete_account(user)

    remaining = await child_service.list_for_user(user.id)
    assert remaining == []
