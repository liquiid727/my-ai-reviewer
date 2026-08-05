"""Periodic convergence for queued/running resume processing runs."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from backend.application.resume_service.runs import reconcile_stale_runs
from backend.celery_app import celery
from backend.infrastructure.db.database import async_session_factory

logger = logging.getLogger(__name__)
_loop_local = threading.local()


def _run_async(coro: Any) -> Any:
    loop = getattr(_loop_local, "loop", None)
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _loop_local.loop = loop
    return loop.run_until_complete(coro)


async def _reconcile(limit: int) -> int:
    async with async_session_factory() as session:
        return await reconcile_stale_runs(session, limit=limit)


@celery.task(name="tasks.resume_watchdog", time_limit=20, max_retries=0)  # type: ignore[untyped-decorator]
def reconcile_resume_runs_task(limit: int = 100) -> int:
    """Mark overdue runs failed; manual retry remains an explicit action."""
    try:
        return int(_run_async(_reconcile(limit)))
    except Exception:
        logger.exception("Resume processing watchdog failed")
        return 0


__all__ = ["reconcile_resume_runs_task"]
