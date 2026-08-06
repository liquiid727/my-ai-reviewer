"""Celery tasks for hybrid_v2 JD matching."""

from __future__ import annotations

import uuid
from typing import Any

from backend.application.jd_matching.service import HybridJDMatchingService, JDMatchingError
from backend.celery_app import celery
from backend.domain.jd.matching_v2 import MatchStatus
from backend.infrastructure.db.celery_database import celery_async_session_factory as async_session_factory
from backend.tasks.async_runtime import run_async


async def _perform(match_id: uuid.UUID, run_id: uuid.UUID) -> str:
    async with async_session_factory() as session:
        return await HybridJDMatchingService().run_match(session, match_id, run_id)


async def _mark_failed(match_id: uuid.UUID, run_id: uuid.UUID, failure_code: str) -> None:
    async with async_session_factory() as session:
        await HybridJDMatchingService().mark_failed(
            session, match_id=match_id, run_id=run_id, failure_code=failure_code
        )


@celery.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="tasks.jd_match_hybrid_v2",
    time_limit=180,
    max_retries=2,
    default_retry_delay=30,
)
def jd_match_hybrid_v2_task(self: Any, match_id_str: str, run_id_str: str) -> str:
    match_id = uuid.UUID(match_id_str)
    run_id = uuid.UUID(run_id_str)
    try:
        return run_async(_perform(match_id, run_id))
    except JDMatchingError as exc:
        if exc.code in {428, 1002, 1003} or self.request.retries >= (self.max_retries or 0):
            run_async(_mark_failed(match_id, run_id, "JD_MATCH_FAILED" if exc.code != 5001 else "JD_MATCH_LLM_INVALID"))
            return MatchStatus.FAILED.value
        raise self.retry(exc=exc)
    except Exception as exc:
        if self.request.retries >= (self.max_retries or 0):
            run_async(_mark_failed(match_id, run_id, "JD_MATCH_FAILED"))
            return MatchStatus.FAILED.value
        raise self.retry(exc=JDMatchingError("JD match analysis failed", 5001)) from exc


def process_jd_match(match_id: str, run_id: str) -> None:
    jd_match_hybrid_v2_task.apply_async(args=(match_id, run_id))
