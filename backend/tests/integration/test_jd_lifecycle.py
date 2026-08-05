"""JD lifecycle command tests (RIP-011 #100)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.jd_lifecycle import (
    JDLifecycleError,
    JDLifecycleUseCases,
    JDReferencedError,
)
from backend.domain.jd.enums import JDProcessingStep, JDStatus
from backend.infrastructure.db.models import JobDescriptionModel
from backend.tests.conftest import requires_db

pytestmark = requires_db


async def _seed_jd(
    session: AsyncSession,
    *,
    status: str = "ready",
    step: str = "done",
    has_version: bool = False,
) -> JobDescriptionModel:
    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Lifecycle JD",
        raw_text="JD",
        status=status,
        processing_step=step,
        review_revision=1,
        review_draft={"title": "Lifecycle JD"} if status == "needs_review" else None,
    )
    session.add(jd)
    await session.commit()
    await session.refresh(jd)
    if has_version:
        from backend.infrastructure.db.models import JobDescriptionVersionModel

        version = JobDescriptionVersionModel(
            id=uuid.uuid4(),
            job_description_id=jd.id,
            version_no=1,
            normalized_text="JD",
            structured={},
            evidence={},
            source_metadata={},
            content_hash="c" * 64,
            parser_version="legacy",
            schema_version="jd-v1",
            publication_reason="legacy_backfill",
        )
        session.add(version)
        await session.flush()
        jd.current_version_id = version.id
        await session.commit()
        await session.refresh(jd)
    return jd


async def test_reparse_ready_preserves_current_version(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session, has_version=True)
    run_id = await JDLifecycleUseCases().start_reparse(db_session, jd.id)
    assert run_id is not None
    await db_session.refresh(jd)
    assert jd.status == JDStatus.PROCESSING.value
    assert jd.processing_step == JDProcessingStep.SOURCE_EXTRACT.value
    # current_version_id remains usable during reparse.
    assert jd.current_version_id is not None


async def test_reparse_keeps_history_untouched(db_session: AsyncSession) -> None:
    from sqlalchemy import select

    from backend.infrastructure.db.models import JobDescriptionVersionModel

    jd = await _seed_jd(db_session, has_version=True)
    before = (
        (
            await db_session.execute(
                select(JobDescriptionVersionModel).where(JobDescriptionVersionModel.job_description_id == jd.id)
            )
        )
        .scalars()
        .all()
    )
    await JDLifecycleUseCases().start_reparse(db_session, jd.id)
    after = (
        (
            await db_session.execute(
                select(JobDescriptionVersionModel).where(JobDescriptionVersionModel.job_description_id == jd.id)
            )
        )
        .scalars()
        .all()
    )
    assert [v.version_no for v in before] == [v.version_no for v in after]


async def test_retry_failed_jd(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session, status="failed", step="done")
    run_id = await JDLifecycleUseCases().retry(db_session, jd.id)
    await db_session.refresh(jd)
    assert run_id is not None
    assert jd.status == JDStatus.PROCESSING.value
    assert jd.processing_step == JDProcessingStep.SOURCE_EXTRACT.value


async def test_retry_not_failed_rejected(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session, status="ready", step="done")
    with pytest.raises(JDLifecycleError):
        await JDLifecycleUseCases().retry(db_session, jd.id)


async def test_abandon_draft_retains_current_version(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session, status="needs_review", step="review", has_version=True)
    await JDLifecycleUseCases().abandon_draft(db_session, jd.id)
    await db_session.refresh(jd)
    assert jd.status == JDStatus.READY.value
    assert jd.review_draft is None
    assert jd.current_version_id is not None


async def test_archive_jd(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session, has_version=True)
    await JDLifecycleUseCases().archive(db_session, jd.id)
    await db_session.refresh(jd)
    assert jd.status == JDStatus.ARCHIVED.value
    assert jd.current_version_id is not None


async def test_referenced_delete_refused(db_session: AsyncSession) -> None:
    from backend.infrastructure.db.models import JobSearchPlanModel, ResumeModel

    jd = await _seed_jd(db_session, has_version=True)
    resume = ResumeModel(id=uuid.uuid4(), status="evaluated", masked_text="[MASKED]")
    db_session.add(resume)
    await db_session.flush()
    plan = JobSearchPlanModel(
        id=uuid.uuid4(),
        jd_id=jd.id,
        resume_id=resume.id,
        title="Plan",
        status="active",
        revision=1,
        generation_run_id=uuid.uuid4(),
    )
    db_session.add(plan)
    await db_session.commit()
    with pytest.raises(JDReferencedError):
        await JDLifecycleUseCases().referenced_delete(db_session, jd.id)
