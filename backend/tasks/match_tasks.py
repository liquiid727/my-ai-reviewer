"""Celery handoff for match assessment evaluation (RIP-013 §7.1/§7.2).

The worker only finalizes under current run ownership: a stale run exits
without a result write, and a dependency/broker failure persists a safe
retryable diagnostic on the same row.
"""

from __future__ import annotations

import uuid
from typing import Any

from backend.application.match_assessment import MatchAssessmentWorker
from backend.celery_app import celery
from backend.infrastructure.db.database import async_session_factory
from backend.tasks.async_runtime import run_async


async def _perform(assessment_id: uuid.UUID, run_id: uuid.UUID) -> str:
    async with async_session_factory() as session:
        return await MatchAssessmentWorker(session=session).evaluate(assessment_id, run_id)


@celery.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="tasks.match_assess",
    time_limit=240,
    max_retries=1,
    default_retry_delay=30,
)
def match_assessment_task(self: Any, assessment_id_str: str, run_id_str: str) -> str:
    """Evaluate once per attempt; only the current run may persist a result."""
    assessment_id = uuid.UUID(assessment_id_str)
    run_id = uuid.UUID(run_id_str)
    try:
        return run_async(_perform(assessment_id, run_id))
    except Exception:
        if self.request.retries >= (self.max_retries or 0):
            return "failed"
        raise self.retry()


def process_match_assessment(assessment_id: str, run_id: str) -> None:
    match_assessment_task.apply_async(args=(assessment_id, run_id))
