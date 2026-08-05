"""Regression coverage for Celery async database work in one worker process."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.domain.resume.enums import ResumeStatus
from backend.tasks import resume_tasks, resume_watchdog
from backend.tests.conftest import TEST_DB_URL, requires_db

pytestmark = requires_db


def test_watchdog_then_resume_task_reuses_a_real_database_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One Celery child can run watchdog then resume work through the same pool."""
    engine = create_async_engine(TEST_DB_URL, pool_size=1, max_overflow=0)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def watchdog_round_trip(session: AsyncSession, *, limit: int) -> int:
        assert limit == 100
        await session.execute(text("SELECT 1"))
        return 0

    async def resume_round_trip(session: AsyncSession, _resume_id: uuid.UUID) -> SimpleNamespace:
        await session.execute(text("SELECT 1"))
        return SimpleNamespace(status=ResumeStatus.TEXT_MASKED.value)

    monkeypatch.setattr(resume_watchdog, "async_session_factory", session_factory)
    monkeypatch.setattr(resume_watchdog, "reconcile_stale_runs", watchdog_round_trip)
    monkeypatch.setattr(resume_tasks, "async_session_factory", session_factory)
    monkeypatch.setattr(resume_tasks.resume_pipeline, "extract_text", resume_round_trip)

    try:
        assert resume_watchdog.reconcile_resume_runs_task.run() == 0
        assert resume_tasks.text_extract_task.run(str(uuid.uuid4())) == ResumeStatus.TEXT_MASKED.value
    finally:
        # The pre-fix code deliberately reaches a cross-loop error. Discarding
        # this test-only pool keeps cleanup independent of that failed loop.
        engine.sync_engine.dispose(close=False)
