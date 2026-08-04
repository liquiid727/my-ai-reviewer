"""Celery task runtime must keep async database work on one event loop."""

from __future__ import annotations

import asyncio

from backend.tasks import resume_tasks


def test_celery_async_runner_reuses_one_event_loop() -> None:
    async def loop_identity() -> int:
        return id(asyncio.get_running_loop())

    first = resume_tasks._run_async(loop_identity())  # type: ignore[attr-defined]
    second = resume_tasks._run_async(loop_identity())  # type: ignore[attr-defined]

    assert first == second
