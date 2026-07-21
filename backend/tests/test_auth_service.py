from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ConflictError, UnauthorizedError
from app.services.auth_service import AuthService


@pytest.fixture
def auth_service(db_session: AsyncSession, settings: Settings) -> AuthService:
    return AuthService(session=db_session, settings=settings)


async def test_register_creates_user(auth_service: AuthService) -> None:
    user = await auth_service.register(
        email="parent@example.com", password="supersecret1", display_name="Parent"
    )
    assert user.id
    assert user.email == "parent@example.com"
    assert user.hashed_password != "supersecret1"


async def test_register_duplicate_email_raises_conflict(auth_service: AuthService) -> None:
    await auth_service.register(
        email="parent@example.com", password="supersecret1", display_name="Parent"
    )
    with pytest.raises(ConflictError):
        await auth_service.register(
            email="parent@example.com", password="anotherpass1", display_name="Someone Else"
        )


async def test_login_success_issues_tokens(auth_service: AuthService) -> None:
    await auth_service.register(
        email="parent@example.com", password="supersecret1", display_name="Parent"
    )
    user, tokens = await auth_service.login(email="parent@example.com", password="supersecret1")
    assert user.email == "parent@example.com"
    assert tokens.access_token
    assert tokens.refresh_token


async def test_login_wrong_password_raises_unauthorized(auth_service: AuthService) -> None:
    await auth_service.register(
        email="parent@example.com", password="supersecret1", display_name="Parent"
    )
    with pytest.raises(UnauthorizedError):
        await auth_service.login(email="parent@example.com", password="wrongpassword")


async def test_login_unknown_email_raises_unauthorized(auth_service: AuthService) -> None:
    with pytest.raises(UnauthorizedError):
        await auth_service.login(email="nobody@example.com", password="supersecret1")


async def test_refresh_rotates_token_and_invalidates_old_one(auth_service: AuthService) -> None:
    await auth_service.register(
        email="parent@example.com", password="supersecret1", display_name="Parent"
    )
    _user, tokens = await auth_service.login(email="parent@example.com", password="supersecret1")

    new_tokens = await auth_service.refresh(refresh_token=tokens.refresh_token)
    assert new_tokens.refresh_token != tokens.refresh_token

    with pytest.raises(UnauthorizedError):
        await auth_service.refresh(refresh_token=tokens.refresh_token)


async def test_refresh_unknown_token_raises_unauthorized(auth_service: AuthService) -> None:
    with pytest.raises(UnauthorizedError):
        await auth_service.refresh(refresh_token="not-a-real-token")


async def test_logout_revokes_refresh_token(auth_service: AuthService) -> None:
    await auth_service.register(
        email="parent@example.com", password="supersecret1", display_name="Parent"
    )
    _user, tokens = await auth_service.login(email="parent@example.com", password="supersecret1")

    await auth_service.logout(refresh_token=tokens.refresh_token)

    with pytest.raises(UnauthorizedError):
        await auth_service.refresh(refresh_token=tokens.refresh_token)


async def test_delete_account_removes_user(auth_service: AuthService) -> None:
    user = await auth_service.register(
        email="parent@example.com", password="supersecret1", display_name="Parent"
    )
    await auth_service.delete_account(user)

    with pytest.raises(UnauthorizedError):
        await auth_service.login(email="parent@example.com", password="supersecret1")
