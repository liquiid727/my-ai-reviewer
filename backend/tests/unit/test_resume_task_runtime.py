"""Celery task runtime must keep async database work on one event loop."""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.pool import NullPool

from backend.domain.resume.enums import ResumeStatus
from backend.infrastructure.db.celery_database import celery_async_engine
from backend.tasks import async_runtime, resume_tasks, resume_watchdog


def test_celery_async_runner_reuses_one_event_loop() -> None:
    async def loop_identity() -> int:
        return id(asyncio.get_running_loop())

    first = resume_tasks._run_async(loop_identity())  # type: ignore[attr-defined]
    second = resume_tasks._run_async(loop_identity())  # type: ignore[attr-defined]

    assert first == second


def test_celery_task_modules_share_one_event_loop() -> None:
    async def loop_identity() -> int:
        return id(asyncio.get_running_loop())

    watchdog_loop = resume_watchdog._run_async(loop_identity())  # type: ignore[attr-defined]
    resume_loop = resume_tasks._run_async(loop_identity())  # type: ignore[attr-defined]

    assert watchdog_loop == resume_loop


def test_celery_database_does_not_pool_asyncpg_connections() -> None:
    assert isinstance(celery_async_engine.pool, NullPool)


def test_celery_async_runner_replaces_loop_after_fork(monkeypatch: pytest.MonkeyPatch) -> None:
    async def loop_identity() -> int:
        return id(asyncio.get_running_loop())

    monkeypatch.setattr(async_runtime.os, "getpid", lambda: 1001)
    parent_loop = async_runtime.run_async(loop_identity())
    monkeypatch.setattr(async_runtime.os, "getpid", lambda: 1002)
    child_loop = async_runtime.run_async(loop_identity())

    assert parent_loop != child_loop


def test_celery_stage_output_uses_wire_status_value(monkeypatch: pytest.MonkeyPatch) -> None:
    class _SessionContext:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
            return None

    async def stage(_session: object, _resume_id: uuid.UUID) -> SimpleNamespace:
        return SimpleNamespace(status=ResumeStatus.TEXT_MASKED)

    monkeypatch.setattr(resume_tasks, "async_session_factory", lambda: _SessionContext())

    result = resume_tasks._run_async(resume_tasks._run_step(stage, uuid.uuid4()))  # type: ignore[arg-type]

    assert result == ResumeStatus.TEXT_MASKED.value
    assert resume_tasks.privacy_allows_llm(result) is True


def test_llm_parse_marks_processing_before_running_extractor(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[ResumeStatus] = []

    async def mark_processing(_resume_id: uuid.UUID, status: ResumeStatus) -> None:
        events.append(status)

    async def run_step(_step: object, _resume_id: uuid.UUID) -> str:
        return ResumeStatus.FACT_EXTRACTED.value

    monkeypatch.setattr(resume_tasks, "_mark_processing", mark_processing)
    monkeypatch.setattr(resume_tasks, "_run_step", run_step)

    result = resume_tasks.llm_parse_task.run(
        ResumeStatus.TEXT_MASKED.value,
        str(uuid.uuid4()),
    )

    assert result == ResumeStatus.FACT_EXTRACTED.value
    assert events == [ResumeStatus.LLM_PARSING]


def test_llm_parse_soft_timeout_is_retried_without_final_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    async def mark_processing(_resume_id: uuid.UUID, _status: ResumeStatus) -> None:
        events.append("processing")

    async def run_step(_step: object, _resume_id: uuid.UUID) -> str:
        raise resume_tasks.SoftTimeLimitExceeded()

    monkeypatch.setattr(resume_tasks, "_mark_processing", mark_processing)
    monkeypatch.setattr(resume_tasks, "_run_step", run_step)

    with pytest.raises(RuntimeError, match="retry scheduled"):
        resume_tasks.llm_parse_task.run(
            ResumeStatus.TEXT_MASKED.value,
            str(uuid.uuid4()),
        )

    assert events == ["processing"]


def test_soft_timeout_after_retry_budget_persists_terminal_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    async def mark_failed(_resume_id: uuid.UUID, _error: BaseException) -> None:
        events.append("failed")

    monkeypatch.setattr(resume_tasks, "_mark_failed", mark_failed)
    task = SimpleNamespace(
        request=SimpleNamespace(retries=2),
        max_retries=2,
    )

    result = resume_tasks._retry_or_fail(
        task,
        resume_id=uuid.uuid4(),
        run_id=None,
        run_id_str=None,
        task_id=None,
        step="llm_parse",
        attempt=3,
        error=resume_tasks.SoftTimeLimitExceeded(),
        error_code=resume_tasks.RESUME_PROCESSING_TIMEOUT,
    )

    assert result == ResumeStatus.FAILED.value
    assert events == ["failed"]


def test_pipeline_signatures_carry_one_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[object] = []
    monkeypatch.setattr(
        resume_tasks,
        "_dispatch_pipeline",
        lambda tasks: captured.extend(tasks) or "task-id",
    )

    resume_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    assert resume_tasks.process_resume_pipeline(resume_id, run_id) == "task-id"

    assert [getattr(signature, "args", ())[-1] for signature in captured] == [run_id] * 4
