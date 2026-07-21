from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db_session
from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.main import app
from app.models import Base
from app.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
    load_knowledge_base_repository,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE_DIR = REPO_ROOT / "knowledge_base"


@pytest.fixture(scope="session")
def kb_dir() -> Path:
    return KNOWLEDGE_BASE_DIR


@pytest.fixture(scope="session")
def kb_repository(kb_dir: Path) -> KnowledgeBaseRepository:
    return load_knowledge_base_repository(kb_dir)


@pytest.fixture
def settings() -> Settings:
    return get_settings()


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """The rate limiter's storage is a process-wide singleton; reset it
    before every test so one test's requests don't trip another's limit.
    """
    limiter.reset()


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """An isolated in-memory SQLite database, fresh for every test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def client(db_session: AsyncSession) -> Iterator[TestClient]:
    """A TestClient wired to the isolated test database instead of dev SQLite."""

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
