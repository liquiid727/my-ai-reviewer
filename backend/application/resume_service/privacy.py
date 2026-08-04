"""Resume privacy review use cases (application layer)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.resume_service.pipeline import detach_resume_file, get_privacy_manifest
from backend.config import get_settings
from backend.domain.privacy import PrivacyGuard, PrivacyManifest, apply_manual_mask_spans
from backend.domain.resume.enums import ResumeStatus
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
    resume.parse_error = "Privacy review expired; upload the resume again"
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


async def approve_privacy_review(
    session: AsyncSession,
    *,
    resume: ResumeModel,
    manifest: ResumePrivacyManifestModel,
) -> dict[str, str]:
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
    await session.commit()
    await asyncio.to_thread(process_masked_resume_pipeline, str(resume.id))
    return {"resume_id": str(resume.id), "status": str(resume.status)}


async def retry_failed_resume(
    session: AsyncSession,
    resume: ResumeModel,
) -> None:
    """Reset a failed resume and dispatch the full pipeline."""
    resume.parse_error = None
    resume.status = ResumeStatus.UPLOADED.value
    await session.commit()
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, process_resume_pipeline, str(resume.id))
    except Exception:
        resume.status = ResumeStatus.FAILED.value
        resume.parse_error = "Failed to dispatch pipeline to broker"
        await session.commit()
        raise


async def reparse_resume(
    session: AsyncSession,
    resume_id: uuid.UUID,
) -> ResumeModel:
    """Snapshot current result, reset status, and dispatch full pipeline."""
    from backend.application.resume_service.pipeline import snapshot_and_reset_for_reparse

    resume = await snapshot_and_reset_for_reparse(session, resume_id)
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, process_resume_pipeline, str(resume.id))
    except Exception:
        resume.status = ResumeStatus.FAILED.value
        resume.parse_error = "Failed to dispatch pipeline to broker"
        await session.commit()
        raise
    return resume
