"""Job Target lifecycle application/API tests (RIP-010 #095)."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.job_target import (
    ArchiveTargetCommand,
    EnsureTargetCommand,
    JobTargetArchivedError,
    JobTargetNotFoundError,
    JobTargetRevisionConflictError,
    JobTargetUseCases,
    UpdateDefaultsCommand,
    VersionScopeMismatchError,
)
from backend.infrastructure.db.models import (
    JobDescriptionModel,
    JobDescriptionVersionModel,
    ResumeModel,
    ResumeVersionModel,
)
from backend.tests.conftest import requires_db

pytestmark = requires_db


async def _seed_jd(session: AsyncSession) -> JobDescriptionModel:
    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Lifecycle JD",
        raw_text="JD",
        status="ready",
        processing_step="done",
    )
    session.add(jd)
    await session.commit()
    await session.refresh(jd)
    return jd


async def _seed_jd_version(session: AsyncSession, jd_id: uuid.UUID) -> JobDescriptionVersionModel:
    version = JobDescriptionVersionModel(
        id=uuid.uuid4(),
        job_description_id=jd_id,
        version_no=1,
        normalized_text="JD",
        structured={},
        evidence={},
        source_metadata={},
        content_hash="a" * 64,
        parser_version="legacy",
        schema_version="jd-v1",
        publication_reason="legacy_backfill",
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version


async def _seed_resume_version(session: AsyncSession) -> ResumeVersionModel:
    resume = ResumeModel(id=uuid.uuid4(), status="evaluated", masked_text="[MASKED]")
    session.add(resume)
    await session.flush()
    version = ResumeVersionModel(
        id=uuid.uuid4(),
        source_type="parsed_resume",
        resume_id=resume.id,
        source_revision=1,
        content_hash="b" * 64,
        masked_snapshot={"masked_text": "[MASKED]"},
        profile_snapshot={},
        evidence_catalog=[],
        parser_version="resume-parser-v3",
        schema_version="resume-v1",
        privacy_policy_version="resume-privacy-v1",
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version


async def test_ensure_creates_active_target(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session)
    result = await JobTargetUseCases().ensure(
        db_session,
        EnsureTargetCommand(jd_id=jd.id),
    )
    assert result.created is True
    assert result.job_description_id == jd.id
    assert result.revision == 1
    assert result.archived_at is None


async def test_ensure_is_idempotent(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session)
    uc = JobTargetUseCases()
    first = await uc.ensure(db_session, EnsureTargetCommand(jd_id=jd.id))
    second = await uc.ensure(db_session, EnsureTargetCommand(jd_id=jd.id))
    assert first.created is True
    assert second.created is False
    assert second.id == first.id


async def test_ensure_sets_default_versions(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session)
    jd_version = await _seed_jd_version(db_session, jd.id)
    resume_version = await _seed_resume_version(db_session)
    result = await JobTargetUseCases().ensure(
        db_session,
        EnsureTargetCommand(
            jd_id=jd.id,
            default_jd_version_id=jd_version.id,
            default_resume_version_id=resume_version.id,
        ),
    )
    assert result.default_jd_version_id == jd_version.id
    assert result.default_resume_version_id == resume_version.id


async def test_ensure_rejects_cross_identity_jd_version(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session)
    other_jd = await _seed_jd(db_session)
    other_version = await _seed_jd_version(db_session, other_jd.id)
    with pytest.raises(VersionScopeMismatchError):
        await JobTargetUseCases().ensure(
            db_session,
            EnsureTargetCommand(jd_id=jd.id, default_jd_version_id=other_version.id),
        )


async def test_update_defaults_revision_safe(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session)
    jd_version = await _seed_jd_version(db_session, jd.id)
    target = await JobTargetUseCases().ensure(db_session, EnsureTargetCommand(jd_id=jd.id))
    updated = await JobTargetUseCases().update_defaults(
        db_session,
        UpdateDefaultsCommand(
            target_id=target.id,
            expected_revision=1,
            default_jd_version_id=jd_version.id,
        ),
    )
    assert updated.default_jd_version_id == jd_version.id
    assert updated.revision == 2


async def test_update_defaults_revision_conflict(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session)
    target = await JobTargetUseCases().ensure(db_session, EnsureTargetCommand(jd_id=jd.id))
    with pytest.raises(JobTargetRevisionConflictError):
        await JobTargetUseCases().update_defaults(
            db_session,
            UpdateDefaultsCommand(target_id=target.id, expected_revision=99),
        )


async def test_update_archived_rejected(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session)
    target = await JobTargetUseCases().ensure(db_session, EnsureTargetCommand(jd_id=jd.id))
    await JobTargetUseCases().archive(
        db_session,
        ArchiveTargetCommand(target_id=target.id, expected_revision=1),
    )
    with pytest.raises(JobTargetArchivedError):
        await JobTargetUseCases().update_defaults(
            db_session,
            UpdateDefaultsCommand(target_id=target.id, expected_revision=2),
        )


async def test_archive_releases_slot_for_new_active(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session)
    first = await JobTargetUseCases().ensure(db_session, EnsureTargetCommand(jd_id=jd.id))
    await JobTargetUseCases().archive(
        db_session,
        ArchiveTargetCommand(target_id=first.id, expected_revision=1),
    )
    second = await JobTargetUseCases().ensure(db_session, EnsureTargetCommand(jd_id=jd.id))
    assert second.created is True
    assert second.id != first.id


async def test_archive_revision_conflict(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session)
    target = await JobTargetUseCases().ensure(db_session, EnsureTargetCommand(jd_id=jd.id))
    with pytest.raises(JobTargetRevisionConflictError):
        await JobTargetUseCases().archive(
            db_session,
            ArchiveTargetCommand(target_id=target.id, expected_revision=5),
        )


async def test_get_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(JobTargetNotFoundError):
        await JobTargetUseCases().get(db_session, uuid.uuid4())


async def test_api_ensure_get_archive_flow(db_session: AsyncSession) -> None:
    from collections.abc import AsyncGenerator

    from backend.infrastructure.db.database import get_db
    from backend.main import app

    jd = await _seed_jd(db_session)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/job-targets", json={"jd_id": str(jd.id)})
    assert resp.status_code == 200
    target = resp.json()["data"]
    assert target["revision"] == 1
    target_id = target["id"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/job-targets/{target_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == target_id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/job-targets/{target_id}/archive",
            json={"expected_revision": 1},
        )
    assert resp.status_code == 200
    assert resp.json()["data"]["archived_at"] is not None
    app.dependency_overrides.clear()


async def test_api_ensure_rejects_cross_identity_version(db_session: AsyncSession) -> None:
    from collections.abc import AsyncGenerator

    from backend.infrastructure.db.database import get_db
    from backend.main import app

    jd = await _seed_jd(db_session)
    other_jd = await _seed_jd(db_session)
    other_version = await _seed_jd_version(db_session, other_jd.id)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/job-targets",
            json={"jd_id": str(jd.id), "default_jd_version_id": str(other_version.id)},
        )
    assert resp.status_code == 422
    app.dependency_overrides.clear()
