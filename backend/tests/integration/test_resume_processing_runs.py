"""Durable ownership and timeout convergence for resume processing."""

from __future__ import annotations

import time
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.resume_service import privacy as privacy_service
from backend.application.resume_service.queries import build_status_payload
from backend.application.resume_service.runs import (
    ERROR_PROCESSING_TIMEOUT,
    RUN_STATUS_FAILED,
    RUN_STATUS_RUNNING,
    RUN_TYPE_RETRY,
    ActiveProcessingRunError,
    create_processing_run,
    dispatch_with_timeout,
    mark_run_dispatched,
    mark_run_failed,
    reconcile_stale_runs,
    utc_now,
)
from backend.domain.resume.enums import ResumeStatus
from backend.infrastructure.db.models import ResumeModel, ResumePrivacyManifestModel, ResumeProcessingRunModel


async def _resume(db_session: AsyncSession, status: str = ResumeStatus.TEXT_MASKED.value) -> ResumeModel:
    resume = ResumeModel(id=uuid.uuid4(), status=status)
    db_session.add(resume)
    await db_session.commit()
    return resume


@pytest.mark.asyncio
async def test_stale_worker_cannot_fail_newer_retry(
    db_session: AsyncSession,
) -> None:
    resume = await _resume(db_session)
    resume_id = resume.id
    first = await create_processing_run(
        db_session,
        resume_id=resume_id,
        run_type=RUN_TYPE_RETRY,
        start_step="llm_parse",
        resume_status=ResumeStatus.TEXT_MASKED.value,
    )
    await db_session.commit()
    assert await mark_run_dispatched(
        db_session,
        resume_id=resume_id,
        run_id=first.id,
        task_id="task-old",
    )

    newer = await create_processing_run(
        db_session,
        resume_id=resume_id,
        run_type=RUN_TYPE_RETRY,
        start_step="llm_parse",
        resume_status=ResumeStatus.TEXT_MASKED.value,
        supersede_active=True,
    )
    await db_session.commit()

    assert (
        await mark_run_failed(
            db_session,
            resume_id=resume_id,
            run_id=first.id,
        )
        is False
    )

    current = await db_session.get(ResumeModel, resume_id)
    old = await db_session.get(ResumeProcessingRunModel, first.id)
    current_run = await db_session.get(ResumeProcessingRunModel, newer.id)
    assert current is not None and current.processing_run_id == newer.id
    assert old is not None and old.status == RUN_STATUS_FAILED
    assert current_run is not None and current_run.status == "queued"


@pytest.mark.asyncio
async def test_watchdog_marks_overdue_run_failed_and_retryable(
    db_session: AsyncSession,
) -> None:
    resume = await _resume(db_session, ResumeStatus.UPLOADED.value)
    resume_id = resume.id
    run = await create_processing_run(
        db_session,
        resume_id=resume_id,
        run_type=RUN_TYPE_RETRY,
        start_step="text_extract",
        resume_status=ResumeStatus.UPLOADED.value,
    )
    await db_session.commit()
    assert await mark_run_dispatched(
        db_session,
        resume_id=resume_id,
        run_id=run.id,
        task_id="task-stuck",
    )

    persisted_run = await db_session.get(ResumeProcessingRunModel, run.id)
    assert persisted_run is not None
    persisted_run.deadline_at = utc_now() - timedelta(seconds=1)
    await db_session.commit()

    assert await reconcile_stale_runs(db_session, limit=10) == 1

    current = await db_session.get(ResumeModel, resume_id)
    failed_run = await db_session.get(ResumeProcessingRunModel, run.id)
    assert current is not None and current.status == ResumeStatus.FAILED.value
    assert current.processing_error_details is not None
    assert current.processing_error_details["error_code"] == "RESUME_PROCESSING_TIMEOUT"
    assert failed_run is not None
    assert failed_run.status == RUN_STATUS_FAILED
    assert failed_run.error_code == ERROR_PROCESSING_TIMEOUT
    assert failed_run.retryable is True


@pytest.mark.asyncio
async def test_active_run_is_unique_until_explicit_retry(
    db_session: AsyncSession,
) -> None:
    resume = await _resume(db_session)
    resume_id = resume.id
    await create_processing_run(
        db_session,
        resume_id=resume_id,
        run_type=RUN_TYPE_RETRY,
        start_step="llm_parse",
        resume_status=ResumeStatus.TEXT_MASKED.value,
    )
    await db_session.commit()

    with pytest.raises(ActiveProcessingRunError):
        await create_processing_run(
            db_session,
            resume_id=resume_id,
            run_type=RUN_TYPE_RETRY,
            start_step="llm_parse",
            resume_status=ResumeStatus.TEXT_MASKED.value,
        )
    await db_session.rollback()

    active_count = await db_session.scalar(
        select(ResumeProcessingRunModel.id).where(
            ResumeProcessingRunModel.resume_id == resume_id,
            ResumeProcessingRunModel.status.in_({"queued", RUN_STATUS_RUNNING, "waiting_review"}),
        )
    )
    assert active_count is not None


@pytest.mark.asyncio
async def test_status_read_lazily_converges_expired_queued_run(
    db_session: AsyncSession,
) -> None:
    resume = await _resume(db_session, ResumeStatus.UPLOADED.value)
    resume_id = resume.id
    run = await create_processing_run(
        db_session,
        resume_id=resume_id,
        run_type=RUN_TYPE_RETRY,
        start_step="text_extract",
        resume_status=ResumeStatus.UPLOADED.value,
    )
    await db_session.commit()

    persisted_run = await db_session.get(ResumeProcessingRunModel, run.id)
    assert persisted_run is not None
    persisted_run.deadline_at = utc_now() - timedelta(seconds=1)
    await db_session.commit()

    payload = await build_status_payload(db_session, resume_id)

    assert payload is not None
    assert payload["status"] == ResumeStatus.FAILED.value
    assert payload["current_step"] == "failed"
    assert payload["error_code"] == "RESUME_PROCESSING_TIMEOUT"
    assert payload["retryable"] is True


@pytest.mark.asyncio
async def test_expired_privacy_review_closes_waiting_run(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume = await _resume(db_session, ResumeStatus.PRIVACY_REVIEW_REQUIRED.value)
    resume_id = resume.id
    manifest = ResumePrivacyManifestModel(
        resume_id=resume_id,
        status="review_required",
        policy_version="test-policy",
        engine_version="test-engine",
        quarantine_path="synthetic/source.enc",
        quarantine_expires_at=utc_now() - timedelta(seconds=1),
    )
    db_session.add(manifest)
    run = await create_processing_run(
        db_session,
        resume_id=resume_id,
        run_type=RUN_TYPE_RETRY,
        start_step="text_extract",
        resume_status=ResumeStatus.UPLOADED.value,
    )
    run.status = "waiting_review"
    run.current_step = "privacy_scan"
    run.deadline_at = None
    await db_session.commit()
    monkeypatch.setattr(privacy_service, "delete_file", lambda *_args: None)

    assert await privacy_service.expire_quarantine_if_needed(db_session, resume, manifest)

    failed_run = await db_session.get(ResumeProcessingRunModel, run.id)
    assert failed_run is not None
    assert failed_run.status == RUN_STATUS_FAILED
    assert failed_run.error_code == "RESUME_PRIVACY_EXPIRED"
    assert failed_run.retryable is False


@pytest.mark.asyncio
async def test_broker_dispatch_has_a_server_side_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Settings:
        RESUME_DISPATCH_TIMEOUT_SECONDS = 0.001

    monkeypatch.setattr("backend.application.resume_service.runs.get_settings", lambda: _Settings())

    def stalled_dispatch() -> None:
        time.sleep(0.02)

    with pytest.raises(TimeoutError):
        await dispatch_with_timeout(stalled_dispatch)
