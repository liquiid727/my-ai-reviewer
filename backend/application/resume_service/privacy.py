"""Resume privacy review use cases (application layer)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.resume_service.diagnostics import (
    RESUME_PIPELINE_DISPATCH_FAILED,
    RESUME_PRIVACY_EXPIRED,
    build_failure_details,
    public_error_message,
)
from backend.application.resume_service.pipeline import detach_resume_file, get_privacy_manifest
from backend.application.resume_service.runs import (
    ERROR_DISPATCH_FAILED,
    RUN_TYPE_REPARSE,
    RUN_TYPE_RETRY,
    activate_waiting_review_run,
    create_processing_run,
    dispatch_with_timeout,
    get_latest_run,
    mark_dispatch_failed,
    mark_run_dispatched,
    reconcile_stale_resume,
)
from backend.config import get_settings
from backend.domain.privacy import PrivacyGuard, PrivacyManifest, apply_manual_mask_spans
from backend.domain.resume.enums import ResumeStatus, resume_status_value
from backend.infrastructure.db.models import FileModel, ResumeModel, ResumePrivacyManifestModel
from backend.infrastructure.storage.minio_client import delete_file
from backend.tasks.resume_tasks import process_masked_resume_pipeline, process_resume_pipeline


async def load_privacy_records(
    session: AsyncSession,
    resume_id: uuid.UUID,
) -> tuple[ResumeModel | None, ResumePrivacyManifestModel | None]:
    resume = await session.get(ResumeModel, resume_id)
    manifest = await get_privacy_manifest(session, resume_id)
    return resume, manifest


async def expire_quarantine_if_needed(
    session: AsyncSession,
    resume: ResumeModel,
    manifest: ResumePrivacyManifestModel,
) -> bool:
    expires = manifest.quarantine_expires_at
    if expires is None or expires > datetime.now(timezone.utc):
        return False
    if manifest.quarantine_path:
        settings = get_settings()
        await asyncio.to_thread(
            delete_file,
            settings.MINIO_BUCKET_QUARANTINE,
            manifest.quarantine_path,
        )
    if resume.file_id is not None:
        file_record = await session.get(FileModel, resume.file_id)
        await detach_resume_file(session, resume, file_record)
    manifest.quarantine_path = None
    manifest.quarantine_expires_at = None
    manifest.status = "expired"
    resume.status = ResumeStatus.FAILED.value
    resume.parse_error = public_error_message(RESUME_PRIVACY_EXPIRED)
    resume.processing_error_details = build_failure_details(
        RESUME_PRIVACY_EXPIRED,
        step="privacy_scan",
        retryable=False,
    )
    if hasattr(session, "execute"):
        run = await get_latest_run(session, resume.id)
        if run is not None and run.status in {"queued", "running", "waiting_review"}:
            now = datetime.now(timezone.utc)
            run.status = "failed"
            run.current_step = "privacy_scan"
            run.last_progress_at = now
            run.finished_at = now
            run.deadline_at = None
            run.error_code = RESUME_PRIVACY_EXPIRED
            run.error_message = public_error_message(RESUME_PRIVACY_EXPIRED)
            run.retryable = False
    await session.commit()
    return True


async def apply_privacy_masks(
    session: AsyncSession,
    *,
    resume: ResumeModel,
    manifest: ResumePrivacyManifestModel,
    spans: list[tuple[int, int, str]],
) -> dict[str, Any]:
    current_manifest = PrivacyManifest(
        policy_version=manifest.policy_version,
        engine_version=manifest.engine_version,
        placeholders=manifest.placeholders,
        risk_flags=manifest.risk_flags,
    )
    result = apply_manual_mask_spans(
        resume.masked_text or "",
        spans,
        existing_manifest=current_manifest,
    )
    resume.masked_text = result.masked_text
    # Rebuild downstream structured blocks from the approved masked text; the
    # previous block snapshot may have omitted a manually selected span.
    resume.parsed_result = {}
    manifest.placeholders = [item.model_dump(mode="json") for item in result.manifest.placeholders]
    manifest.revision += 1
    await session.commit()
    return {
        "status": manifest.status,
        "revision": manifest.revision,
        "masked_text": resume.masked_text,
        "placeholders": manifest.placeholders,
    }


def is_processing_stale(resume: ResumeModel, *, now: datetime | None = None) -> bool:
    """Return whether an in-flight resume task is old enough to requeue safely."""
    active_statuses = {
        ResumeStatus.TEXT_MASKED.value,
        ResumeStatus.LLM_PARSING.value,
        ResumeStatus.EVALUATING.value,
    }
    if resume_status_value(resume.status) not in active_statuses:
        return False

    updated_at = cast(datetime | None, getattr(resume, "updated_at", None))
    if updated_at is None:
        return True
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    cutoff = timedelta(seconds=get_settings().RESUME_STALE_PROCESSING_SECONDS)
    return (now or datetime.now(timezone.utc)) - updated_at >= cutoff


async def approve_privacy_review(
    session: AsyncSession,
    *,
    resume: ResumeModel,
    manifest: ResumePrivacyManifestModel,
) -> dict[str, str | None]:
    PrivacyGuard().assert_masked(resume.masked_text or "")

    quarantine_path = manifest.quarantine_path
    if quarantine_path:
        settings = get_settings()
        await asyncio.to_thread(delete_file, settings.MINIO_BUCKET_QUARANTINE, quarantine_path)
    if resume.file_id is not None:
        file_record = await session.get(FileModel, resume.file_id)
        await detach_resume_file(session, resume, file_record)
    manifest.status = "approved"
    manifest.reviewed_at = datetime.now(timezone.utc)
    manifest.quarantine_path = None
    manifest.quarantine_expires_at = None
    manifest.risk_flags = []
    resume.status = ResumeStatus.TEXT_MASKED.value
    if not hasattr(session, "execute"):
        # Lightweight unit-test/session doubles from the pre-run contract.
        await session.commit()
        await asyncio.to_thread(process_masked_resume_pipeline, str(resume.id))
        return {"resume_id": str(resume.id), "status": resume_status_value(resume.status)}

    run = await activate_waiting_review_run(
        session,
        resume_id=resume.id,
        start_step="llm_parse",
    )
    await session.commit()
    try:
        task_id = await dispatch_with_timeout(
            process_masked_resume_pipeline,
            str(resume.id),
            str(run.id),
        )
        if not task_id:
            raise RuntimeError("Pipeline dispatch returned no task id")
        await mark_run_dispatched(
            session,
            resume_id=resume.id,
            run_id=run.id,
            task_id=task_id,
        )
    except Exception:
        await mark_dispatch_failed(session, resume_id=resume.id, run_id=run.id)
    return {
        "resume_id": str(resume.id),
        "status": resume_status_value(resume.status),
        "run_id": str(run.id),
        "error_code": ERROR_DISPATCH_FAILED if resume.status == ResumeStatus.FAILED.value else None,
    }


async def retry_failed_resume(
    session: AsyncSession,
    resume: ResumeModel,
) -> str:
    """Reset a failed/stale resume and dispatch the safe matching pipeline."""
    if not hasattr(session, "execute"):
        return await _retry_failed_resume_legacy(session, resume)

    # A retry request is also a convergence point for an orphaned worker.  It
    # never requeues automatically; it only makes a manual retry safe.
    await reconcile_stale_resume(session, resume.id)
    refreshed = await session.get(ResumeModel, resume.id)
    if refreshed is None:
        raise ValueError(f"Resume not found: {resume.id}")
    resume = refreshed
    status = resume_status_value(resume.status)
    stale_statuses = {
        ResumeStatus.TEXT_MASKED.value,
        ResumeStatus.LLM_PARSING.value,
        ResumeStatus.EVALUATING.value,
    }
    manifest = await get_privacy_manifest(session, resume.id)
    masked_ready = bool(resume.masked_text) and manifest is not None and manifest.status == "approved"

    latest_run = await get_latest_run(session, resume.id)
    active_run = latest_run is not None and latest_run.status in {
        "queued",
        "running",
        "waiting_review",
    }
    if status in stale_statuses:
        if active_run or not is_processing_stale(resume):
            raise ValueError("Resume processing is still active")
        if not masked_ready:
            raise ValueError("Approved masked resume is not available")
        use_masked_pipeline = True
    elif status == ResumeStatus.FAILED.value:
        if masked_ready:
            use_masked_pipeline = True
        elif resume.file_id is None:
            raise ValueError("Original resume quarantine is no longer available")
        else:
            use_masked_pipeline = False
    else:
        raise ValueError("Resume is not retryable")

    run = await create_processing_run(
        session,
        resume_id=resume.id,
        run_type=RUN_TYPE_RETRY,
        start_step="llm_parse" if use_masked_pipeline else "text_extract",
        resume_status=ResumeStatus.TEXT_MASKED.value if use_masked_pipeline else ResumeStatus.UPLOADED.value,
    )
    await session.commit()
    try:
        if use_masked_pipeline:
            task_id = await dispatch_with_timeout(
                process_masked_resume_pipeline,
                str(resume.id),
                str(run.id),
            )
        else:
            if resume.file_id is None:
                raise ValueError("Original resume quarantine is no longer available")
            task_id = await dispatch_with_timeout(
                process_resume_pipeline,
                str(resume.id),
                str(run.id),
            )
        if not task_id:
            raise RuntimeError("Pipeline dispatch returned no task id")
        await mark_run_dispatched(
            session,
            resume_id=resume.id,
            run_id=run.id,
            task_id=task_id,
        )
    except Exception:
        await mark_dispatch_failed(session, resume_id=resume.id, run_id=run.id)
    return resume.status


async def _retry_failed_resume_legacy(
    session: AsyncSession,
    resume: ResumeModel,
) -> str:
    """Compatibility path for isolated session doubles without run storage."""
    status = resume_status_value(resume.status)
    stale_statuses = {
        ResumeStatus.TEXT_MASKED.value,
        ResumeStatus.LLM_PARSING.value,
        ResumeStatus.EVALUATING.value,
    }
    manifest = await get_privacy_manifest(session, resume.id)
    masked_ready = bool(resume.masked_text) and manifest is not None and manifest.status == "approved"
    if status in stale_statuses:
        if not is_processing_stale(resume):
            raise ValueError("Resume processing is still active")
        if not masked_ready:
            raise ValueError("Approved masked resume is not available")
        use_masked_pipeline = True
    elif status == ResumeStatus.FAILED.value:
        use_masked_pipeline = masked_ready
    else:
        raise ValueError("Resume is not retryable")

    resume.parse_error = None
    resume.status = ResumeStatus.TEXT_MASKED.value if use_masked_pipeline else ResumeStatus.UPLOADED.value
    await session.commit()
    try:
        if use_masked_pipeline:
            await asyncio.to_thread(process_masked_resume_pipeline, str(resume.id))
        else:
            if resume.file_id is None:
                raise ValueError("Original resume quarantine is no longer available")
            await asyncio.to_thread(process_resume_pipeline, str(resume.id))
    except Exception:
        resume.status = ResumeStatus.FAILED.value
        resume.parse_error = public_error_message(RESUME_PIPELINE_DISPATCH_FAILED)
        resume.processing_error_details = build_failure_details(
            RESUME_PIPELINE_DISPATCH_FAILED,
            step="dispatch",
            retryable=True,
        )
        await session.commit()
        raise
    return resume.status


async def reparse_resume(
    session: AsyncSession,
    resume_id: uuid.UUID,
) -> ResumeModel:
    """Snapshot current result, reset status, and dispatch full pipeline."""
    from backend.application.resume_service.pipeline import snapshot_and_reset_for_reparse

    # Keep the snapshot, run supersession, and new ownership pointer in one
    # transaction.  Committing the reset before creating the run would leave a
    # window where the old worker could still publish progress.
    resume = await snapshot_and_reset_for_reparse(session, resume_id, commit=False)
    if not hasattr(session, "execute"):
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, process_resume_pipeline, str(resume.id))
        except Exception:
            resume.status = ResumeStatus.FAILED.value
            resume.parse_error = public_error_message(RESUME_PIPELINE_DISPATCH_FAILED)
            resume.processing_error_details = build_failure_details(
                RESUME_PIPELINE_DISPATCH_FAILED,
                step="dispatch",
                retryable=True,
            )
            await session.commit()
            raise
        return resume

    run = await create_processing_run(
        session,
        resume_id=resume.id,
        run_type=RUN_TYPE_REPARSE,
        start_step="text_extract",
        resume_status=ResumeStatus.UPLOADED.value,
        supersede_active=True,
    )
    await session.commit()
    try:
        task_id = await dispatch_with_timeout(
            process_resume_pipeline,
            str(resume.id),
            str(run.id),
        )
        if not task_id:
            raise RuntimeError("Pipeline dispatch returned no task id")
        await mark_run_dispatched(
            session,
            resume_id=resume.id,
            run_id=run.id,
            task_id=task_id,
        )
    except Exception:
        await mark_dispatch_failed(session, resume_id=resume.id, run_id=run.id)
    return resume
