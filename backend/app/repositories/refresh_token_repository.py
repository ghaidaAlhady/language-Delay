"""Data access for refresh tokens."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


async def create(
    session: AsyncSession, *, user_id: str, token_hash: str, expires_at: datetime
) -> RefreshToken:
    refresh_token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    session.add(refresh_token)
    await session.flush()
    return refresh_token


async def get_valid_by_hash(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token = result.scalar_one_or_none()
    if token is None or token.revoked_at is not None:
        return None
    if token.expires_at < datetime.now(UTC):
        return None
    return token


async def revoke(session: AsyncSession, refresh_token: RefreshToken) -> None:
    refresh_token.revoked_at = datetime.now(UTC)
    await session.flush()


async def revoke_all_for_user(session: AsyncSession, user_id: str) -> None:
    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
        )
    )
    now = datetime.now(UTC)
    for token in result.scalars():
        token.revoked_at = now
    await session.flush()
