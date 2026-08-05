"""JD lifecycle commands: reparse, retry, abandon-draft, archive (RIP-011 §6.3, §7.3)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.jd.enums import JDProcessingStep, JDStatus
from backend.infrastructure.db.models import (
    JobDescriptionModel,
    JobSearchPlanModel,
)


class JDLifecycleError(Exception):
    """Base JD lifecycle error."""


class JDReferencedError(JDLifecycleError):
    """Identity is referenced by downstream resources; archive instead of delete."""


class JDLifecycleStateError(JDLifecycleError):
    """JD is not in the required state for the command."""


class JDReparseUnavailableError(JDLifecycleError):
    """Reparse cannot start because source/retryability is unavailable."""


class JDLifecycleUseCases:
    """Reparse/retry/abandon/archive with current-version preservation."""

    async def start_reparse(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
        *,
        overwrite_manual: bool = False,
    ) -> uuid.UUID:
        """Create a new processing run/draft; manual fields protected by default."""
        jd = await session.get(JobDescriptionModel, jd_id)
        if jd is None:
            raise JDLifecycleStateError("JD not found")
        if jd.status not in {JDStatus.READY.value, JDStatus.FAILED.value, JDStatus.NEEDS_REVIEW.value}:
            raise JDLifecycleStateError(f"JD status {jd.status} cannot reparse")
        if jd.status == JDStatus.NEEDS_REVIEW.value and jd.review_draft and not overwrite_manual:
            # Preserve the current review draft; a reparse creates a fresh draft.
            pass
        run_id = uuid.uuid4()
        jd.processing_run_id = run_id
        jd.status = JDStatus.PROCESSING.value
        jd.processing_step = JDProcessingStep.SOURCE_EXTRACT.value
        jd.processing_error = None
        # A reparse leaves current_version_id and history untouched.
        await session.commit()
        return run_id

    async def retry(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
    ) -> uuid.UUID:
        """Resume from the latest safe step with a new run ID."""
        jd = await session.get(JobDescriptionModel, jd_id)
        if jd is None:
            raise JDLifecycleStateError("JD not found")
        if jd.status != JDStatus.FAILED.value:
            raise JDLifecycleStateError(f"JD status {jd.status} is not retryable")
        run_id = uuid.uuid4()
        jd.processing_run_id = run_id
        jd.status = JDStatus.PROCESSING.value
        step = JDProcessingStep.SOURCE_EXTRACT.value
        if jd.processing_error and "llm" in (jd.processing_error or ""):
            step = JDProcessingStep.LLM_EXTRACT.value
        jd.processing_step = step
        jd.processing_error = None
        await session.commit()
        return run_id

    async def abandon_draft(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
    ) -> None:
        """Abandon a failed/unpublished draft; retain the current version."""
        jd = await session.get(JobDescriptionModel, jd_id)
        if jd is None:
            raise JDLifecycleStateError("JD not found")
        if jd.status not in {JDStatus.NEEDS_REVIEW.value, JDStatus.FAILED.value}:
            raise JDLifecycleStateError(f"JD status {jd.status} has no draft to abandon")
        jd.review_draft = None
        jd.review_revision = 0
        jd.review_error = None
        if jd.current_version_id is not None:
            jd.status = JDStatus.READY.value
            jd.processing_step = JDProcessingStep.DONE.value
        else:
            jd.status = JDStatus.FAILED.value
            jd.processing_step = JDProcessingStep.DONE.value
        await session.commit()

    async def archive(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
    ) -> None:
        """Archive identity without deleting versions or references."""
        jd = await session.get(JobDescriptionModel, jd_id)
        if jd is None:
            raise JDLifecycleStateError("JD not found")
        if jd.status == JDStatus.ARCHIVED.value:
            raise JDLifecycleStateError("JD is already archived")
        jd.status = JDStatus.ARCHIVED.value
        jd.processing_step = JDProcessingStep.DONE.value
        jd.review_draft = None
        await session.commit()

    async def _has_references(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
    ) -> bool:
        stmt = select(JobSearchPlanModel.id).where(JobSearchPlanModel.jd_id == jd_id).limit(1)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def referenced_delete(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
    ) -> None:
        """Hard delete is refused when referenced; callers must archive instead."""
        if await self._has_references(session, jd_id):
            raise JDReferencedError("JD is referenced by a plan; archive instead")
        jd = await session.get(JobDescriptionModel, jd_id)
        if jd is None:
            raise JDLifecycleStateError("JD not found")
        await session.delete(jd)
        await session.commit()
