import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.config import get_settings
from backend.infrastructure.db.models import Base
from backend.main import app

settings = get_settings()

TEST_DB_URL = (
    settings.DATABASE_URL.replace("/ai_interview", "/ai_interview_test")
    if "/ai_interview" in settings.DATABASE_URL
    else settings.DATABASE_URL + "_test"
)

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionFactory = async_sessionmaker(test_engine, expire_on_commit=False)


def _db_available() -> bool:
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(TEST_DB_URL.replace("+asyncpg", ""))
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    try:
        sock = socket.create_connection((host, port), timeout=1)
        sock.close()
        return True
    except OSError:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason=f"Test database not reachable at {TEST_DB_URL}",
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from backend.infrastructure.db.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_resume(db_session: AsyncSession):
    from backend.infrastructure.db.models import ResumeModel

    resume = ResumeModel(
        id=uuid.uuid4(),
        status="evaluated",
        raw_text="Test resume content",
        parsed_result={
            "profile": {"name": "Test User", "email": "test@example.com"},
            "classification": {"experience_level": "Mid"},
        },
    )
    db_session.add(resume)
    await db_session.commit()
    await db_session.refresh(resume)
    return resume
