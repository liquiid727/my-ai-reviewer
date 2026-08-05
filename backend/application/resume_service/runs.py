"""Durable ownership and timeout handling for resume processing runs.

The resume row stores the user-visible result. This module stores the
execution attempt that is allowed to write that result. Every worker write
must carry ``run_id`` and pass through these guards so an old Celery task can
finish harmlessly after a manual retry or re-parse has started.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any, Final, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.resume_service.diagnostics import (
    RESUME_LLM_REQUEST_TIMEOUT,
    RESUME_PIPELINE_DISPATCH_FAILED,
    RESUME_PROCESSING_FAILED,
    RESUME_PROCESSING_TIMEOUT,
    build_failure_details,
    public_error_message,
)
from backend.config import get_settings
from backend.domain.resume.enums import ResumeStatus, resume_status_value
from backend.infrastructure.db.models import ResumeModel, ResumeProcessingRunModel

RUN_STATUS_QUEUED: Final = "queued"
RUN_STATUS_RUNNING: Final = "running"
RUN_STATUS_WAITING_REVIEW: Final = "waiting_review"
RUN_STATUS_SUCCEEDED: Final = "succeeded"
RUN_STATUS_FAILED: Final = "failed"
ACTIVE_RUN_STATUSES: Final = frozenset({RUN_STATUS_QUEUED, RUN_STATUS_RUNNING, RUN_STATUS_WAITING_REVIEW})

RUN_TYPE_UPLOAD: Final = "upload"
RUN_TYPE_MASKED: Final = "masked"
RUN_TYPE_RETRY: Final = "retry"
RUN_TYPE_REPARSE: Final = "reparse"

STEP_TIMEOUT_SECONDS: Final[dict[str, int]] = {
    "text_extract": 30,
    "llm_parse": 120,
    "classify": 30,
    "evaluate": 120,
}
NEXT_STEP: Final[dict[str, str]] = {
    "text_extract": "llm_parse",
    "llm_parse": "classify",
    "classify": "evaluate",
    "evaluate": "done",
}
IN_FLIGHT_RESUME_STATUS: Final[dict[str, str]] = {
    "text_extract": ResumeStatus.PRIVACY_SCANNING.value,
    "llm_parse": ResumeStatus.LLM_PARSING.value,
    "evaluate": ResumeStatus.EVALUATING.value,
}

ERROR_DISPATCH_FAILED: Final = RESUME_PIPELINE_DISPATCH_FAILED
ERROR_PROCESSING_TIMEOUT: Final = RESUME_PROCESSING_TIMEOUT
ERROR_WORKER_LOST: Final = RESUME_PROCESSING_TIMEOUT
ERROR_PROVIDER_TIMEOUT: Final = RESUME_LLM_REQUEST_TIMEOUT
ERROR_PROCESSING_FAILED: Final = RESUME_PROCESSING_FAILED
ERROR_SUPERSEDED: Final = RESUME_PROCESSING_FAILED

SAFE_ERROR_MESSAGES: Final[dict[str, str]] = {
    ERROR_DISPATCH_FAILED: public_error_message(ERROR_DISPATCH_FAILED),
    ERROR_PROCESSING_TIMEOUT: public_error_message(ERROR_PROCESSING_TIMEOUT),
    ERROR_WORKER_LOST: public_error_message(ERROR_WORKER_LOST),
    ERROR_PROVIDER_TIMEOUT: public_error_message(ERROR_PROVIDER_TIMEOUT),
    ERROR_PROCESSING_FAILED: public_error_message(ERROR_PROCESSING_FAILED),
    ERROR_SUPERSEDED: public_error_message(ERROR_SUPERSEDED),
}


class ActiveProcessingRunError(ValueError):
    """Raised when a resume already has an active execution owner."""


_DispatchResult = TypeVar("_DispatchResult")


async def dispatch_with_timeout(
    dispatcher: Callable[..., _DispatchResult],
    *args: Any,
) -> _DispatchResult:
    """Bound the broker handoff; a late thread can only target a failed run."""
    return await asyncio.wait_for(
        asyncio.to_thread(dispatcher, *args),
        timeout=get_settings().RESUME_DISPATCH_TIMEOUT_SECONDS,
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def safe_error_message(error_code: str) -> str:
    return SAFE_ERROR_MESSAGES.get(error_code, SAFE_ERROR_MESSAGES[ERROR_PROCESSING_FAILED])


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _step_deadline(step: str, now: datetime) -> datetime:
    seconds = STEP_TIMEOUT_SECONDS.get(step, 120)
    return now + timedelta(seconds=seconds)


def _initial_resume_status(step: str) -> str:
    if step == "llm_parse":
        return ResumeStatus.TEXT_MASKED.value
    return ResumeStatus.UPLOADED.value


async def _lock_resume(session: AsyncSession, resume_id: uuid.UUID) -> ResumeModel | None:
    result = await session.execute(select(ResumeModel).where(ResumeModel.id == resume_id).with_for_update())
    return result.scalar_one_or_none()


async def _lock_run(
    session: AsyncSession,
    resume_id: uuid.UUID,
    run_id: uuid.UUID,
) -> ResumeProcessingRunModel | None:
    result = await session.execute(
        select(ResumeProcessingRunModel)
        .where(
            ResumeProcessingRunModel.id == run_id,
            ResumeProcessingRunModel.resume_id == resume_id,
        )
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def _active_run(
    session: AsyncSession,
    resume_id: uuid.UUID,
) -> ResumeProcessingRunModel | None:
    result = await session.execute(
        select(ResumeProcessingRunModel)
        .where(
            ResumeProcessingRunModel.resume_id == resume_id,
            ResumeProcessingRunModel.status.in_(ACTIVE_RUN_STATUSES),
        )
        .order_by(ResumeProcessingRunModel.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    return result.scalar_one_or_none()


def _supersede(run: ResumeProcessingRunModel, now: datetime) -> None:
    run.status = RUN_STATUS_FAILED
    run.finished_at = now
    run.last_progress_at = now
    run.deadline_at = None
    run.error_code = ERROR_SUPERSEDED
    run.error_message = safe_error_message(ERROR_SUPERSEDED)
    run.retryable = True


def _new_run(
    *,
    resume_id: uuid.UUID,
    run_type: str,
    start_step: str,
    now: datetime,
) -> ResumeProcessingRunModel:
    dispatch_deadline = now + timedelta(seconds=get_settings().RESUME_DISPATCH_TIMEOUT_SECONDS)
    return ResumeProcessingRunModel(
        id=uuid.uuid4(),
        resume_id=resume_id,
        run_type=run_type,
        status=RUN_STATUS_QUEUED,
        current_step=start_step,
        attempt=1,
        last_progress_at=now,
        deadline_at=dispatch_deadline,
        retryable=False,
    )


async def create_processing_run(
    session: AsyncSession,
    *,
    resume_id: uuid.UUID,
    run_type: str,
    start_step: str,
    resume_status: str | ResumeStatus | None = None,
    supersede_active: bool = False,
) -> ResumeProcessingRunModel:
    """Create one queued run while serializing against retry/reparse requests."""
    resume = await _lock_resume(session, resume_id)
    if resume is None:
        raise ValueError(f"Resume not found: {resume_id}")
    active = await _active_run(session, resume_id)
    now = utc_now()
    if active is not None:
        if not supersede_active:
            raise ActiveProcessingRunError("Resume already has an active processing run")
        _supersede(active, now)

    run = _new_run(resume_id=resume_id, run_type=run_type, start_step=start_step, now=now)
    session.add(run)
    resume.processing_error_details = None
    resume.status = resume_status_value(resume_status or _initial_resume_status(start_step))
    resume.parse_error = None
    # The schema deliberately has foreign keys in both directions.  Insert the
    # run first, then update the denormalized pointer, otherwise PostgreSQL can
    # flush the parent UPDATE before the referenced run row exists.
    await session.flush()
    # Keep a denormalized current pointer for conditional UPDATEs in worker
    # hot paths; the run table remains the source of execution history.
    resume.processing_run_id = run.id
    await session.flush()
    return run


async def activate_waiting_review_run(
    session: AsyncSession,
    *,
    resume_id: uuid.UUID,
    start_step: str,
) -> ResumeProcessingRunModel:
    """Resume the upload run after privacy approval without duplicating it."""
    resume = await _lock_resume(session, resume_id)
    if resume is None:
        raise ValueError(f"Resume not found: {resume_id}")
    active = await _active_run(session, resume_id)
    now = utc_now()
    if active is None:
        run = _new_run(
            resume_id=resume_id,
            run_type=RUN_TYPE_MASKED,
            start_step=start_step,
            now=now,
        )
        session.add(run)
    elif active.status == RUN_STATUS_WAITING_REVIEW:
        run = active
        run.status = RUN_STATUS_QUEUED
        run.current_step = start_step
        run.last_progress_at = now
        run.deadline_at = now + timedelta(seconds=get_settings().RESUME_DISPATCH_TIMEOUT_SECONDS)
        run.finished_at = None
        run.error_code = None
        run.error_message = None
        run.retryable = False
    else:
        raise ActiveProcessingRunError("Resume already has an active processing run")
    resume.processing_error_details = None
    resume.status = ResumeStatus.TEXT_MASKED.value
    resume.parse_error = None
    await session.flush()
    resume.processing_run_id = run.id
    await session.flush()
    return run


async def mark_run_dispatched(
    session: AsyncSession,
    *,
    resume_id: uuid.UUID,
    run_id: uuid.UUID,
    task_id: str | None,
) -> bool:
    """Record a successful broker handoff and start the step deadline."""
    resume = await _lock_resume(session, resume_id)
    run = await _lock_run(session, resume_id, run_id) if resume is not None else None
    if resume is None or run is None or run.status != RUN_STATUS_QUEUED:
        await session.rollback()
        return False
    now = utc_now()
    run.status = RUN_STATUS_RUNNING
    run.celery_task_id = task_id
    run.last_progress_at = now
    run.deadline_at = _step_deadline(run.current_step, now)
    await session.commit()
    return True


async def mark_dispatch_failed(
    session: AsyncSession,
    *,
    resume_id: uuid.UUID,
    run_id: uuid.UUID,
) -> bool:
    """Persist a broker handoff failure so the API never leaves ``uploaded`` forever."""
    resume = await _lock_resume(session, resume_id)
    run = await _lock_run(session, resume_id, run_id) if resume is not None else None
    if resume is None or run is None or run.status not in ACTIVE_RUN_STATUSES:
        await session.rollback()
        return False
    _mark_failed_locked(resume, run, ERROR_DISPATCH_FAILED, utc_now())
    await session.commit()
    return True


async def claim_run_step(
    session: AsyncSession,
    *,
    resume_id: uuid.UUID,
    run_id: uuid.UUID,
    step: str,
    task_id: str | None,
    attempt: int,
) -> bool:
    """Claim a step; an old run or expired worker can only become a no-op."""
    resume = await _lock_resume(session, resume_id)
    run = await _lock_run(session, resume_id, run_id) if resume is not None else None
    if resume is None or run is None or run.status not in ACTIVE_RUN_STATUSES:
        await session.rollback()
        return False

    now = utc_now()
    deadline = _aware(run.deadline_at)
    if deadline is not None and deadline <= now:
        code = ERROR_WORKER_LOST if run.status == RUN_STATUS_QUEUED else ERROR_PROCESSING_TIMEOUT
        _mark_failed_locked(resume, run, code, now)
        await session.commit()
        return False
    if run.status == RUN_STATUS_WAITING_REVIEW or run.current_step not in {step, ""}:
        await session.rollback()
        return False

    run.status = RUN_STATUS_RUNNING
    run.current_step = step
    run.celery_task_id = task_id
    run.attempt = max(1, attempt)
    run.last_progress_at = now
    run.deadline_at = _step_deadline(step, now)
    run.error_code = None
    run.error_message = None
    run.retryable = False
    in_flight = IN_FLIGHT_RESUME_STATUS.get(step)
    if in_flight is not None:
        resume.status = in_flight
        resume.parse_error = None
        resume.processing_error_details = None
    await session.commit()
    return True


async def complete_run_step(
    session: AsyncSession,
    *,
    resume_id: uuid.UUID,
    run_id: uuid.UUID,
    step: str,
    result_status: str | ResumeStatus,
    task_id: str | None = None,
    attempt: int | None = None,
) -> str:
    """Advance the run only when the worker still owns the current step."""
    resume = await _lock_resume(session, resume_id)
    run = await _lock_run(session, resume_id, run_id) if resume is not None else None
    if resume is None or run is None or run.status not in ACTIVE_RUN_STATUSES or run.current_step != step:
        await session.rollback()
        return "stale"

    status = resume_status_value(result_status)
    now = utc_now()
    run.last_progress_at = now
    if task_id is not None:
        run.celery_task_id = task_id
    if attempt is not None:
        run.attempt = max(1, attempt)
    if status == ResumeStatus.PRIVACY_REVIEW_REQUIRED.value:
        run.status = RUN_STATUS_WAITING_REVIEW
        run.current_step = "privacy_scan"
        run.deadline_at = None
    elif status == ResumeStatus.FAILED.value:
        _mark_failed_locked(resume, run, ERROR_PROCESSING_FAILED, now)
    elif status == ResumeStatus.EVALUATED.value or step == "evaluate":
        run.status = RUN_STATUS_SUCCEEDED
        run.current_step = "done"
        run.deadline_at = None
        run.finished_at = now
        run.error_code = None
        run.error_message = None
        run.retryable = False
        resume.processing_error_details = None
    else:
        next_step = NEXT_STEP.get(step, "done")
        run.current_step = next_step
        run.deadline_at = None if next_step == "done" else _step_deadline(next_step, now)
    await session.commit()
    return status


def _mark_failed_locked(
    resume: ResumeModel,
    run: ResumeProcessingRunModel,
    error_code: str,
    now: datetime,
    *,
    retryable: bool = True,
) -> None:
    diagnostic_code = {
        ERROR_DISPATCH_FAILED: RESUME_PIPELINE_DISPATCH_FAILED,
        ERROR_PROCESSING_TIMEOUT: RESUME_PROCESSING_TIMEOUT,
        ERROR_WORKER_LOST: RESUME_PROCESSING_TIMEOUT,
        ERROR_PROVIDER_TIMEOUT: RESUME_LLM_REQUEST_TIMEOUT,
        ERROR_PROCESSING_FAILED: RESUME_PROCESSING_FAILED,
    }.get(error_code, RESUME_PROCESSING_FAILED)
    run.status = RUN_STATUS_FAILED
    run.finished_at = now
    run.last_progress_at = now
    run.deadline_at = None
    run.error_code = error_code
    run.error_message = safe_error_message(error_code)
    run.retryable = retryable
    resume.status = ResumeStatus.FAILED.value
    resume.parse_error = public_error_message(diagnostic_code)
    resume.processing_error_details = build_failure_details(
        diagnostic_code,
        step=run.current_step,
        attempt=run.attempt,
        retryable=retryable,
    )


async def mark_run_failed(
    session: AsyncSession,
    *,
    resume_id: uuid.UUID,
    run_id: uuid.UUID,
    error_code: str = ERROR_PROCESSING_FAILED,
) -> bool:
    """Fail the run conditionally; stale workers cannot overwrite a newer run."""
    resume = await _lock_resume(session, resume_id)
    run = await _lock_run(session, resume_id, run_id) if resume is not None else None
    if resume is None or run is None or run.status not in ACTIVE_RUN_STATUSES:
        await session.rollback()
        return False
    _mark_failed_locked(resume, run, error_code, utc_now())
    await session.commit()
    return True


async def reconcile_stale_resume(
    session: AsyncSession,
    resume_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> bool:
    """Lazily converge one expired run when its status endpoint is read."""
    resume = await _lock_resume(session, resume_id)
    run = await _active_run(session, resume_id) if resume is not None else None
    if resume is None or run is None:
        await session.rollback()
        return False
    current = now or utc_now()
    deadline = _aware(run.deadline_at)
    if deadline is None or deadline > current:
        await session.rollback()
        return False
    code = ERROR_WORKER_LOST if run.status == RUN_STATUS_QUEUED else ERROR_PROCESSING_TIMEOUT
    _mark_failed_locked(resume, run, code, current)
    await session.commit()
    return True


async def reconcile_stale_runs(
    session: AsyncSession,
    *,
    limit: int = 100,
    now: datetime | None = None,
) -> int:
    """Watchdog scan; mark overdue work failed but never auto-requeue it."""
    current = now or utc_now()
    result = await session.execute(
        select(ResumeProcessingRunModel.resume_id)
        .where(
            ResumeProcessingRunModel.status.in_({RUN_STATUS_QUEUED, RUN_STATUS_RUNNING}),
            ResumeProcessingRunModel.deadline_at.is_not(None),
            ResumeProcessingRunModel.deadline_at <= current,
        )
        .order_by(ResumeProcessingRunModel.deadline_at)
        .limit(limit)
    )
    resume_ids = list(result.scalars().all())
    await session.rollback()
    reconciled = 0
    for resume_id in resume_ids:
        if await reconcile_stale_resume(session, resume_id, now=current):
            reconciled += 1
    return reconciled


async def get_latest_run(
    session: AsyncSession,
    resume_id: uuid.UUID,
) -> ResumeProcessingRunModel | None:
    result = await session.execute(
        select(ResumeProcessingRunModel)
        .where(ResumeProcessingRunModel.resume_id == resume_id)
        .order_by(ResumeProcessingRunModel.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def load_owned_resume(
    session: AsyncSession,
    *,
    resume_id: uuid.UUID,
    run_id: uuid.UUID,
) -> ResumeModel | None:
    """Load a resume only while ``run_id`` is still an active owner."""
    resume = await _lock_resume(session, resume_id)
    run = await _lock_run(session, resume_id, run_id) if resume is not None else None
    if resume is None or run is None or run.status not in ACTIVE_RUN_STATUSES or resume.processing_run_id != run_id:
        return None
    return resume


__all__ = [
    "ACTIVE_RUN_STATUSES",
    "ActiveProcessingRunError",
    "ERROR_DISPATCH_FAILED",
    "ERROR_PROCESSING_FAILED",
    "ERROR_PROCESSING_TIMEOUT",
    "ERROR_PROVIDER_TIMEOUT",
    "ERROR_WORKER_LOST",
    "RUN_STATUS_FAILED",
    "RUN_STATUS_QUEUED",
    "RUN_STATUS_RUNNING",
    "RUN_STATUS_SUCCEEDED",
    "RUN_STATUS_WAITING_REVIEW",
    "RUN_TYPE_MASKED",
    "RUN_TYPE_REPARSE",
    "RUN_TYPE_RETRY",
    "RUN_TYPE_UPLOAD",
    "STEP_TIMEOUT_SECONDS",
    "activate_waiting_review_run",
    "claim_run_step",
    "complete_run_step",
    "create_processing_run",
    "dispatch_with_timeout",
    "get_latest_run",
    "load_owned_resume",
    "mark_dispatch_failed",
    "mark_run_dispatched",
    "mark_run_failed",
    "reconcile_stale_resume",
    "reconcile_stale_runs",
    "safe_error_message",
    "utc_now",
]
