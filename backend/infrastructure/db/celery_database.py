"""Database sessions for Celery workers.

Celery tasks may run different async entry points in the same prefork
worker.  A NullPool prevents an asyncpg connection bound to one event loop
from being reused by another loop or by a forked child process.  The web API
continues to use the pooled engine in ``database.py``.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.config import get_settings

settings = get_settings()

celery_async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,
    pool_pre_ping=True,
)

celery_async_session_factory = async_sessionmaker(
    celery_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


__all__ = ["celery_async_engine", "celery_async_session_factory"]
