"""Celery stages for JD source extraction, de-duplication, and LLM extraction."""

from __future__ import annotations

import asyncio
import threading
import uuid
from typing import Any

from celery import chain

from backend.application.jd_service.processing import JDProcessingError, JDProcessingService
from backend.celery_app import celery
from backend.domain.jd.enums import JDProcessingStep, JDStatus
from backend.infrastructure.db.database import async_session_factory

_loop_local = threading.local()


def _run_async(coro: Any) -> Any:
    """Reuse one event loop per worker thread (asyncpg/SQLAlchemy engine binding)."""
    loop = getattr(_loop_local, "loop", None)
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _loop_local.loop = loop
    return loop.run_until_complete(coro)


async def _run_stage(
    stage: str,
    jd_id: uuid.UUID,
    run_id: uuid.UUID,
    *,
    allow_duplicate: bool = False,
    overwrite_manual: bool = False,
    propagate_failure: bool = False,
) -> str:
    async with async_session_factory() as session:
        service = JDProcessingService()
        try:
            if stage == JDProcessingStep.SOURCE_EXTRACT.value:
                return await service.source_extract(session, jd_id, run_id)
            if stage == JDProcessingStep.DUPLICATE_CHECK.value:
                return await service.duplicate_check(
                    session,
                    jd_id,
                    run_id,
                    allow_duplicate=allow_duplicate,
                )
            return await service.llm_extract(session, jd_id, run_id, overwrite_manual=overwrite_manual)
        except Exception as exc:
            if propagate_failure:
                raise
            await service.mark_failed(session, jd_id, run_id, stage, exc)
            return JDStatus.FAILED.value


async def _mark_stage_failed(
    stage: str,
    jd_id: uuid.UUID,
    run_id: uuid.UUID,
    error: Exception,
) -> str:
    async with async_session_factory() as session:
        await JDProcessingService().mark_failed(session, jd_id, run_id, stage, error)
    return JDStatus.FAILED.value


@celery.task(name="tasks.jd_source_extract", time_limit=30, max_retries=0)  # type: ignore[untyped-decorator]
def jd_source_extract_task(jd_id_str: str, run_id_str: str) -> str:
    return _run_async(_run_stage(JDProcessingStep.SOURCE_EXTRACT.value, uuid.UUID(jd_id_str), uuid.UUID(run_id_str)))


@celery.task(name="tasks.jd_duplicate_check", time_limit=30, max_retries=0)  # type: ignore[untyped-decorator]
def jd_duplicate_check_task(
    previous: str,
    jd_id_str: str,
    run_id_str: str,
    allow_duplicate: bool,
) -> str:
    if previous in {"stale", JDStatus.FAILED.value, JDStatus.DUPLICATE_PENDING.value}:
        return previous
    return _run_async(
        _run_stage(
            JDProcessingStep.DUPLICATE_CHECK.value,
            uuid.UUID(jd_id_str),
            uuid.UUID(run_id_str),
            allow_duplicate=allow_duplicate,
        )
    )


@celery.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="tasks.jd_llm_extract",
    time_limit=120,
    max_retries=2,
    default_retry_delay=30,
)
def jd_llm_extract_task(
    self: Any,
    previous: str,
    jd_id_str: str,
    run_id_str: str,
    overwrite_manual: bool,
) -> str:
    if previous in {"stale", JDStatus.FAILED.value, JDStatus.DUPLICATE_PENDING.value}:
        return previous
    jd_id = uuid.UUID(jd_id_str)
    run_id = uuid.UUID(run_id_str)
    try:
        return _run_async(
            _run_stage(
                JDProcessingStep.LLM_EXTRACT.value,
                jd_id,
                run_id,
                overwrite_manual=overwrite_manual,
                propagate_failure=True,
            )
        )
    except Exception as exc:
        safe_error = (
            exc
            if isinstance(exc, JDProcessingError)
            else JDProcessingError(
                "JD structured extraction failed",
                code=5001,
            )
        )
        if self.request.retries >= (self.max_retries or 0):
            return _run_async(_mark_stage_failed(JDProcessingStep.LLM_EXTRACT.value, jd_id, run_id, safe_error))
        raise self.retry(exc=safe_error)


def process_jd_pipeline(
    jd_id: str,
    run_id: str,
    allow_duplicate: bool = False,
    start_step: str | None = None,
    overwrite_manual: bool = False,
) -> None:
    """Queue a fresh run; a stale run's writes are rejected by the service."""
    if start_step == JDProcessingStep.LLM_EXTRACT.value:
        jd_llm_extract_task.apply_async(args=("processing", jd_id, run_id, overwrite_manual))
        return
    pipeline = chain(
        jd_source_extract_task.s(jd_id, run_id),
        jd_duplicate_check_task.s(jd_id, run_id, allow_duplicate),
        jd_llm_extract_task.s(jd_id, run_id, overwrite_manual),
    )
    pipeline.apply_async()
