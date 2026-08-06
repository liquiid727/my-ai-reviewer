"""Celery tasks for the resume pipeline.

Every task carries the current ``run_id``.  A worker that no longer owns that
run exits with ``stale`` and cannot overwrite a newer retry or reparse.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from celery import chain
from celery.exceptions import SoftTimeLimitExceeded

from backend.application.resume_service import pipeline as resume_pipeline
from backend.application.resume_service.diagnostics import (
    RESUME_LLM_REQUEST_TIMEOUT,
    RESUME_PROCESSING_FAILED,
    RESUME_PROCESSING_TIMEOUT,
    build_failure_details,
    error_code_for_exception,
    public_error_message,
)
from backend.application.resume_service.runs import (
    claim_run_step,
    complete_run_step,
    load_owned_resume,
)
from backend.celery_app import celery
from backend.config import get_settings
from backend.domain.resume.enums import ResumeStatus, resume_status_value
from backend.infrastructure.db.celery_database import celery_async_session_factory as async_session_factory
from backend.infrastructure.db.models import ResumeModel, ResumeProcessingRunModel
from backend.observability.context import bind_resume_context
from backend.observability.events import emit_resume_event
from backend.tasks.async_runtime import run_async

logger = logging.getLogger(__name__)

_settings = get_settings()
_LLM_MAX_RETRIES = 2
_RETRY_DELAY_SECONDS = 30


def privacy_allows_llm(status: str | ResumeStatus) -> bool:
    return resume_status_value(status) == ResumeStatus.TEXT_MASKED.value


async def _run_step(
    step_fn: Callable[..., Awaitable[ResumeModel | None]],
    resume_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
) -> str:
    """Run one application step and convert the result to a wire status."""

    async with async_session_factory() as session:
        if run_id is None:
            resume = await step_fn(session, resume_id)
        else:
            if await load_owned_resume(session, resume_id=resume_id, run_id=run_id) is None:
                return "stale"
            resume = await step_fn(session, resume_id, run_id)
        if resume is None:
            return "stale"
        return resume_status_value(resume.status)


async def _mark_processing(
    resume_id: uuid.UUID,
    status: ResumeStatus,
    run_id: uuid.UUID | None = None,
    *,
    step: str | None = None,
    task_id: str | None = None,
    attempt: int = 1,
) -> bool:
    """Set an in-flight status only when this run still owns the resume."""

    if run_id is not None:
        if step is None:
            raise ValueError("step is required for a run-owned task")
        async with async_session_factory() as session:
            return await claim_run_step(
                session,
                resume_id=resume_id,
                run_id=run_id,
                step=step,
                task_id=task_id,
                attempt=attempt,
            )

    async with async_session_factory() as session:
        resume = await session.get(ResumeModel, resume_id)
        if resume is None:
            await session.rollback()
            return False
        resume.status = status.value
        resume.parse_error = None
        resume.processing_error_details = None
        await session.commit()
        return True


async def _mark_run_progress(
    resume_id: uuid.UUID,
    run_id: uuid.UUID | None,
    *,
    status: str,
    step: str,
    task_id: str | None,
    attempt: int,
) -> bool:
    """Advance the run record only when the current step still belongs to it."""

    if run_id is None:
        return True
    async with async_session_factory() as session:
        completed = await complete_run_step(
            session,
            resume_id=resume_id,
            run_id=run_id,
            step=step,
            result_status=status,
            task_id=task_id,
            attempt=attempt,
        )
        return completed != "stale"


async def _mark_failed(
    resume_id: uuid.UUID,
    error: BaseException,
    *,
    run_id: uuid.UUID | None = None,
    step: str = "unknown",
    attempt: int = 1,
    task_id: str | None = None,
    error_code: str | None = None,
    retryable: bool = False,
) -> bool:
    """Persist a safe error summary and close only the current run."""

    code = error_code or error_code_for_exception(error)
    async with async_session_factory() as session:
        resume = (
            await load_owned_resume(session, resume_id=resume_id, run_id=run_id)
            if run_id is not None
            else await session.get(ResumeModel, resume_id)
        )
        if resume is None:
            await session.rollback()
            return False
        resume.status = ResumeStatus.FAILED.value
        resume.parse_error = public_error_message(code)
        resume.processing_error_details = build_failure_details(
            code,
            step=step,
            attempt=attempt,
            retryable=retryable,
            task_id=task_id,
        )
        if run_id is not None:
            run = await session.get(ResumeProcessingRunModel, run_id)
            if run is not None and run.resume_id == resume_id:
                run.status = "failed"
                run.current_step = step
                run.attempt = attempt
                run.celery_task_id = task_id
                run.error_code = code
                run.error_message = public_error_message(code)
                run.retryable = retryable
                run.last_progress_at = _utcnow()
                run.finished_at = _utcnow()
                run.deadline_at = None
                run.error_message = public_error_message(code)
        await session.commit()
        return True


def _utcnow() -> Any:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def _request_info(task: Any) -> tuple[str | None, int]:
    request = getattr(task, "request", None)
    return getattr(request, "id", None), int(getattr(request, "retries", 0) or 0) + 1


def _run_uuid(run_id_str: str | None) -> uuid.UUID | None:
    return uuid.UUID(run_id_str) if run_id_str else None


def _execute_step(
    step_fn: Callable[..., Awaitable[ResumeModel | None]],
    resume_id: uuid.UUID,
    run_id: uuid.UUID | None,
) -> str:
    if run_id is None:
        return run_async(_run_step(step_fn, resume_id))
    return run_async(_run_step(step_fn, resume_id, run_id))


def _emit_started(resource_id: str, run_id: str | None, task_id: str | None, step: str, attempt: int) -> float:
    started = time.monotonic()
    emit_resume_event(
        "resume.stage.started",
        resource_id=resource_id,
        run_id=run_id,
        task_id=task_id,
        step=step,
        attempt=attempt,
    )
    return started


def _emit_completed(
    resource_id: str,
    run_id: str | None,
    task_id: str | None,
    step: str,
    attempt: int,
    status: str,
    started: float,
) -> None:
    emit_resume_event(
        "resume.stage.completed",
        resource_id=resource_id,
        run_id=run_id,
        task_id=task_id,
        step=step,
        attempt=attempt,
        status=status,
        duration_ms=int((time.monotonic() - started) * 1000),
    )


def _retry_or_fail(
    task: Any,
    *,
    resume_id: uuid.UUID,
    run_id: uuid.UUID | None,
    run_id_str: str | None,
    task_id: str | None,
    step: str,
    attempt: int,
    error: BaseException,
    error_code: str,
    duration_ms: int | None = None,
) -> str:
    retries = int(getattr(task.request, "retries", 0) or 0)
    max_retries = int(getattr(task, "max_retries", _LLM_MAX_RETRIES) or 0)
    resource_id = str(resume_id)
    retryable_error = error_code in {RESUME_LLM_REQUEST_TIMEOUT, RESUME_PROCESSING_TIMEOUT} or type(error).__name__ in {
        "TimeoutError",
        "TimeoutException",
        "APITimeoutError",
        "APIConnectionError",
        "RateLimitError",
    }

    def fail_now(*, can_retry_manually: bool) -> None:
        if run_id is None:
            # Preserve the small two-argument seam used by legacy task tests.
            run_async(_mark_failed(resume_id, error))
        else:
            run_async(
                _mark_failed(
                    resume_id,
                    error,
                    run_id=run_id,
                    step=step,
                    attempt=attempt,
                    task_id=task_id,
                    error_code=error_code,
                    retryable=can_retry_manually,
                )
            )

    # Provider/network timeouts are transient and may use the bounded Celery
    # retry budget. Parser/privacy/schema failures fail immediately.
    if not retryable_error:
        fail_now(can_retry_manually=True)
        emit_resume_event(
            "resume.stage.failed",
            resource_id=resource_id,
            run_id=run_id_str,
            task_id=task_id,
            step=step,
            attempt=attempt,
            status=ResumeStatus.FAILED.value,
            error_code=error_code,
            retryable=True,
            level=logging.ERROR,
            duration_ms=duration_ms,
        )
        return ResumeStatus.FAILED.value

    if retries >= max_retries:
        fail_now(can_retry_manually=True)
        emit_resume_event(
            "resume.stage.failed",
            resource_id=resource_id,
            run_id=run_id_str,
            task_id=task_id,
            step=step,
            attempt=attempt,
            status=ResumeStatus.FAILED.value,
            error_code=error_code,
            retryable=True,
            level=logging.ERROR,
            duration_ms=duration_ms,
        )
        return ResumeStatus.FAILED.value

    emit_resume_event(
        "resume.stage.retry_scheduled",
        resource_id=resource_id,
        run_id=run_id_str,
        task_id=task_id,
        step=step,
        attempt=attempt,
        error_code=error_code,
        retryable=True,
        level=logging.WARNING,
        duration_ms=duration_ms,
    )
    # Do not put the provider exception into Celery result data or the retry
    # message; it can contain request/response content.
    raise task.retry(
        exc=RuntimeError("Resume processing retry scheduled"),
        countdown=_RETRY_DELAY_SECONDS,
    )


@celery.task(
    bind=True,
    name="tasks.text_extract",
    time_limit=30,
    soft_time_limit=25,
    max_retries=0,
)  # type: ignore[untyped-decorator]
def text_extract_task(self: Any, resume_id_str: str, run_id_str: str | None = None) -> str:
    """Extract and locally redact the uploaded document."""

    resume_id = uuid.UUID(resume_id_str)
    task_id, attempt = _request_info(self)
    run_id = _run_uuid(run_id_str)
    with bind_resume_context(
        resource_id=resume_id_str,
        run_id=run_id_str,
        task_id=task_id,
        step="text_extract",
        attempt=attempt,
    ):
        started = _emit_started(resume_id_str, run_id_str, task_id, "text_extract", attempt)
        try:
            result = _execute_step(resume_pipeline.extract_text, resume_id, run_id)
            if result == "stale":
                emit_resume_event(
                    "resume.stage.stale_ignored",
                    resource_id=resume_id_str,
                    run_id=run_id_str,
                    task_id=task_id,
                    step="text_extract",
                    attempt=attempt,
                )
                return result
            if result == ResumeStatus.FAILED.value:
                failed_written = run_async(
                    _mark_failed(
                        resume_id,
                        RuntimeError("Resume text extraction failed"),
                        run_id=run_id,
                        step="text_extract",
                        attempt=attempt,
                        task_id=task_id,
                    )
                )
                if failed_written is False:
                    return "stale"
            else:
                progress_written = run_async(
                    _mark_run_progress(
                        resume_id,
                        run_id,
                        status=result,
                        step="text_extract",
                        task_id=task_id,
                        attempt=attempt,
                    )
                )
                if not progress_written:
                    return "stale"
            _emit_completed(resume_id_str, run_id_str, task_id, "text_extract", attempt, result, started)
            return result
        except Exception as exc:
            emit_resume_event(
                "resume.stage.failed",
                resource_id=resume_id_str,
                run_id=run_id_str,
                task_id=task_id,
                step="text_extract",
                attempt=attempt,
                error_code=error_code_for_exception(exc),
                retryable=False,
                level=logging.ERROR,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            run_async(
                _mark_failed(
                    resume_id,
                    exc,
                    run_id=run_id,
                    step="text_extract",
                    attempt=attempt,
                    task_id=task_id,
                )
            )
            return ResumeStatus.FAILED.value


@celery.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="tasks.llm_parse",
    time_limit=_settings.RESUME_LLM_TIME_LIMIT_SECONDS,
    soft_time_limit=_settings.RESUME_LLM_SOFT_TIME_LIMIT_SECONDS,
    max_retries=_LLM_MAX_RETRIES,
    default_retry_delay=_RETRY_DELAY_SECONDS,
)
def llm_parse_task(
    self: Any,
    prev_status: str,
    resume_id_str: str,
    run_id_str: str | None = None,
) -> str:
    """Extract structured facts from masked text with bounded retries."""

    previous = resume_status_value(prev_status)
    if not privacy_allows_llm(previous):
        return previous
    resume_id = uuid.UUID(resume_id_str)
    run_id = _run_uuid(run_id_str)
    task_id, attempt = _request_info(self)
    with bind_resume_context(
        resource_id=resume_id_str,
        run_id=run_id_str,
        task_id=task_id,
        step="llm_parse",
        attempt=attempt,
    ):
        started = _emit_started(resume_id_str, run_id_str, task_id, "llm_parse", attempt)
        try:
            if run_id is None:
                processing_marked = run_async(_mark_processing(resume_id, ResumeStatus.LLM_PARSING))
            else:
                processing_marked = run_async(
                    _mark_processing(
                        resume_id,
                        ResumeStatus.LLM_PARSING,
                        run_id,
                        step="llm_parse",
                        task_id=task_id,
                        attempt=attempt,
                    )
                )
            if processing_marked is False:
                return "stale"
            result = _execute_step(resume_pipeline.extract_facts, resume_id, run_id)
            if result == "stale":
                return result
            progress_written = run_async(
                _mark_run_progress(
                    resume_id,
                    run_id,
                    status=result,
                    step="llm_parse",
                    task_id=task_id,
                    attempt=attempt,
                )
            )
            if not progress_written:
                return "stale"
            _emit_completed(resume_id_str, run_id_str, task_id, "llm_parse", attempt, result, started)
            return result
        except SoftTimeLimitExceeded as exc:
            return _retry_or_fail(
                self,
                resume_id=resume_id,
                run_id=run_id,
                run_id_str=run_id_str,
                task_id=task_id,
                step="llm_parse",
                attempt=attempt,
                error=exc,
                error_code=RESUME_PROCESSING_TIMEOUT,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        except Exception as exc:
            return _retry_or_fail(
                self,
                resume_id=resume_id,
                run_id=run_id,
                run_id_str=run_id_str,
                task_id=task_id,
                step="llm_parse",
                attempt=attempt,
                error=exc,
                error_code=(
                    RESUME_LLM_REQUEST_TIMEOUT
                    if error_code_for_exception(exc) == RESUME_LLM_REQUEST_TIMEOUT
                    else RESUME_PROCESSING_FAILED
                ),
                duration_ms=int((time.monotonic() - started) * 1000),
            )


@celery.task(
    bind=True,
    name="tasks.classify",
    time_limit=30,
    soft_time_limit=25,
    max_retries=0,
)  # type: ignore[untyped-decorator]
def classify_task(
    self: Any,
    prev_status: str,
    resume_id_str: str,
    run_id_str: str | None = None,
) -> str:
    """Classify the extracted profile with bounded, local work."""

    previous = resume_status_value(prev_status)
    if previous != ResumeStatus.FACT_EXTRACTED.value:
        return previous
    resume_id = uuid.UUID(resume_id_str)
    run_id = _run_uuid(run_id_str)
    task_id, attempt = _request_info(self)
    with bind_resume_context(
        resource_id=resume_id_str,
        run_id=run_id_str,
        task_id=task_id,
        step="classify",
        attempt=attempt,
    ):
        started = _emit_started(resume_id_str, run_id_str, task_id, "classify", attempt)
        try:
            result = _execute_step(resume_pipeline.classify_resume, resume_id, run_id)
            if result == "stale":
                return result
            progress_written = run_async(
                _mark_run_progress(
                    resume_id,
                    run_id,
                    status=result,
                    step="classify",
                    task_id=task_id,
                    attempt=attempt,
                )
            )
            if not progress_written:
                return "stale"
            _emit_completed(resume_id_str, run_id_str, task_id, "classify", attempt, result, started)
            return result
        except Exception as exc:
            run_async(
                _mark_failed(
                    resume_id,
                    exc,
                    run_id=run_id,
                    step="classify",
                    attempt=attempt,
                    task_id=task_id,
                )
            )
            emit_resume_event(
                "resume.stage.failed",
                resource_id=resume_id_str,
                run_id=run_id_str,
                task_id=task_id,
                step="classify",
                attempt=attempt,
                error_code=error_code_for_exception(exc),
                retryable=False,
                level=logging.ERROR,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            return ResumeStatus.FAILED.value


@celery.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="tasks.evaluate",
    time_limit=_settings.RESUME_LLM_TIME_LIMIT_SECONDS,
    soft_time_limit=_settings.RESUME_LLM_SOFT_TIME_LIMIT_SECONDS,
    max_retries=_LLM_MAX_RETRIES,
    default_retry_delay=_RETRY_DELAY_SECONDS,
)
def evaluate_task(
    self: Any,
    prev_status: str,
    resume_id_str: str,
    run_id_str: str | None = None,
) -> str:
    """Generate the evaluation with the same bounded retry policy."""

    previous = resume_status_value(prev_status)
    if previous != ResumeStatus.CLASSIFIED.value:
        return previous
    resume_id = uuid.UUID(resume_id_str)
    run_id = _run_uuid(run_id_str)
    task_id, attempt = _request_info(self)
    with bind_resume_context(
        resource_id=resume_id_str,
        run_id=run_id_str,
        task_id=task_id,
        step="evaluate",
        attempt=attempt,
    ):
        started = _emit_started(resume_id_str, run_id_str, task_id, "evaluate", attempt)
        try:
            if run_id is None:
                processing_marked = run_async(_mark_processing(resume_id, ResumeStatus.EVALUATING))
            else:
                processing_marked = run_async(
                    _mark_processing(
                        resume_id,
                        ResumeStatus.EVALUATING,
                        run_id,
                        step="evaluate",
                        task_id=task_id,
                        attempt=attempt,
                    )
                )
            if processing_marked is False:
                return "stale"
            result = _execute_step(resume_pipeline.evaluate_resume, resume_id, run_id)
            if result == "stale":
                return result
            progress_written = run_async(
                _mark_run_progress(
                    resume_id,
                    run_id,
                    status=result,
                    step="evaluate",
                    task_id=task_id,
                    attempt=attempt,
                )
            )
            if not progress_written:
                return "stale"
            _emit_completed(resume_id_str, run_id_str, task_id, "evaluate", attempt, result, started)
            return result
        except SoftTimeLimitExceeded as exc:
            return _retry_or_fail(
                self,
                resume_id=resume_id,
                run_id=run_id,
                run_id_str=run_id_str,
                task_id=task_id,
                step="evaluate",
                attempt=attempt,
                error=exc,
                error_code=RESUME_PROCESSING_TIMEOUT,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        except Exception as exc:
            return _retry_or_fail(
                self,
                resume_id=resume_id,
                run_id=run_id,
                run_id_str=run_id_str,
                task_id=task_id,
                step="evaluate",
                attempt=attempt,
                error=exc,
                error_code=(
                    RESUME_LLM_REQUEST_TIMEOUT
                    if error_code_for_exception(exc) == RESUME_LLM_REQUEST_TIMEOUT
                    else RESUME_PROCESSING_FAILED
                ),
                duration_ms=int((time.monotonic() - started) * 1000),
            )


def _dispatch_pipeline(tasks: Any) -> str | None:
    pipeline = chain(*tasks)
    result = pipeline.apply_async()
    return str(getattr(result, "id", "")) or None


def process_resume_pipeline(resume_id: str, run_id: str | None = None) -> str | None:
    """Dispatch the full pipeline with one run id across all stages."""

    task_id = _dispatch_pipeline(
        [
            text_extract_task.s(resume_id, run_id),
            llm_parse_task.s(resume_id, run_id),
            classify_task.s(resume_id, run_id),
            evaluate_task.s(resume_id, run_id),
        ]
    )
    emit_resume_event(
        "resume.pipeline.dispatched",
        resource_id=resume_id,
        run_id=run_id,
        step="text_extract",
    )
    return task_id


def process_masked_resume_pipeline(resume_id: str, run_id: str | None = None) -> str | None:
    """Dispatch a privacy-approved pipeline beginning at LLM parsing."""

    task_id = _dispatch_pipeline(
        [
            llm_parse_task.s(ResumeStatus.TEXT_MASKED.value, resume_id, run_id),
            classify_task.s(resume_id, run_id),
            evaluate_task.s(resume_id, run_id),
        ]
    )
    emit_resume_event(
        "resume.pipeline.dispatched",
        resource_id=resume_id,
        run_id=run_id,
        step="llm_parse",
    )
    return task_id
