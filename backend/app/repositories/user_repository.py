"""Data access for parent/guardian accounts."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_id(session: AsyncSession, user_id: str) -> User | None:
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create(
    session: AsyncSession, *, email: str, hashed_password: str, display_name: str
) -> User:
    user = User(email=email, hashed_password=hashed_password, display_name=display_name)
    session.add(user)
    await session.flush()
    return user


async def delete(session: AsyncSession, user: User) -> None:
    await session.delete(user)
