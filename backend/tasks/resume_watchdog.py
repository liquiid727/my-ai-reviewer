"""Periodic convergence for queued/running resume processing runs."""

from __future__ import annotations

import logging

from backend.application.resume_service.runs import reconcile_stale_runs
from backend.celery_app import celery
from backend.infrastructure.db.database import async_session_factory
from backend.tasks.async_runtime import run_async

logger = logging.getLogger(__name__)


async def _reconcile(limit: int) -> int:
    async with async_session_factory() as session:
        return await reconcile_stale_runs(session, limit=limit)


@celery.task(name="tasks.resume_watchdog", time_limit=20, max_retries=0)  # type: ignore[untyped-decorator]
def reconcile_resume_runs_task(limit: int = 100) -> int:
    """Mark overdue runs failed; manual retry remains an explicit action."""
    try:
        return int(run_async(_reconcile(limit)))
    except Exception:
        logger.exception("Resume processing watchdog failed")
        return 0


__all__ = ["reconcile_resume_runs_task"]
