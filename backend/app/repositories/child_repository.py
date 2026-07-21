"""Data access for child profiles."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.child import Child


async def get_by_id(session: AsyncSession, child_id: str) -> Child | None:
    return await session.get(Child, child_id)


async def list_for_user(session: AsyncSession, user_id: str) -> list[Child]:
    result = await session.execute(
        select(Child).where(Child.user_id == user_id).order_by(Child.created_at)
    )
    return list(result.scalars())


async def create(session: AsyncSession, *, user_id: str, **fields: object) -> Child:
    child = Child(user_id=user_id, **fields)
    session.add(child)
    await session.flush()
    return child


async def delete(session: AsyncSession, child: Child) -> None:
    await session.delete(child)
