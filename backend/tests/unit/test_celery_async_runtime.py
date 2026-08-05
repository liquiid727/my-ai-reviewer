"""Celery task modules must share one worker-local asyncio runtime."""

from __future__ import annotations

import asyncio

import pytest

from backend.tasks import interview_tasks, jd_tasks, plan_tasks, resume_tasks, resume_watchdog


async def _loop_identity() -> int:
    return id(asyncio.get_running_loop())


def test_all_celery_task_modules_share_one_worker_event_loop() -> None:
    """A pooled asyncpg connection must never move between task-module loops."""
    runners = (
        resume_tasks.run_async,
        resume_watchdog.run_async,
        jd_tasks.run_async,
        plan_tasks.run_async,
        interview_tasks.run_async,
    )

    loop_ids = {runner(_loop_identity()) for runner in runners}

    assert len(loop_ids) == 1


def test_worker_process_initialization_discards_inherited_connection_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each prefork child starts with a fresh SQLAlchemy pool."""
    from backend.tasks import async_runtime

    disposed: list[bool] = []
    monkeypatch.setattr(
        async_runtime.async_engine.sync_engine,
        "dispose",
        lambda *, close: disposed.append(close),
    )

    async_runtime.initialize_worker_process()

    assert disposed == [False]
