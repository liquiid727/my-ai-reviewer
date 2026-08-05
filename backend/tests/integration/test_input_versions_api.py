"""Input version application/API tests (RIP-010 #094)."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.input_versions import (
    PrivacyRejectedError,
    PublishResumeVersionCommand,
    ResumeVersionUseCases,
    SourceNotReadyError,
    SourceRevisionChangedError,
)
from backend.infrastructure.db.models import (
    ResumeDraftModel,
    ResumeModel,
)
from backend.tests.conftest import requires_db

pytestmark = requires_db


async def _seed_evaluated_resume(session: AsyncSession) -> ResumeModel:
    resume = ResumeModel(
        id=uuid.uuid4(),
        status="evaluated",
        masked_text="[MASKED] Candidate has Go experience [MASKED]",
        parsed_result={
            "profile": {"name": "[MASKED]", "email": "[MASKED]"},
            "facts": [{"skill": "Go", "confidence": 0.9}],
            "classification": {"experience_level": "Senior"},
        },
        parser_version="resume-parser-v3",
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)
    return resume


async def _seed_builder_draft(session: AsyncSession, *, revision: int = 1) -> ResumeDraftModel:
    draft = ResumeDraftModel(
        id=uuid.uuid4(),
        title="Draft",
        content={"profile": {"name": "[MASKED]"}, "skills": ["Go"]},
        privacy_manifest={"policy_version": "resume-privacy-v1"},
        revision=revision,
    )
    session.add(draft)
    await session.commit()
    await session.refresh(draft)
    return draft


async def test_publish_parsed_resume_creates_version(db_session: AsyncSession) -> None:
    resume = await _seed_evaluated_resume(db_session)
    result = await ResumeVersionUseCases().publish_or_resolve(
        db_session,
        PublishResumeVersionCommand(source_type="parsed_resume", resume_id=resume.id),
    )
    assert result.created is True
    assert result.source_type == "parsed_resume"
    assert result.schema_version == "resume-v1"
    assert result.content_hash


async def test_publish_parsed_resume_idempotent(db_session: AsyncSession) -> None:
    resume = await _seed_evaluated_resume(db_session)
    uc = ResumeVersionUseCases()
    first = await uc.publish_or_resolve(
        db_session,
        PublishResumeVersionCommand(source_type="parsed_resume", resume_id=resume.id),
    )
    second = await uc.publish_or_resolve(
        db_session,
        PublishResumeVersionCommand(source_type="parsed_resume", resume_id=resume.id),
    )
    assert first.created is True
    assert second.created is False
    assert second.id == first.id


async def test_publish_not_evaluated_rejected(db_session: AsyncSession) -> None:
    resume = ResumeModel(id=uuid.uuid4(), status="uploaded", masked_text="raw", parsed_result={})
    db_session.add(resume)
    await db_session.commit()
    with pytest.raises(SourceNotReadyError):
        await ResumeVersionUseCases().publish_or_resolve(
            db_session,
            PublishResumeVersionCommand(source_type="parsed_resume", resume_id=resume.id),
        )


async def test_publish_builder_revision_race(db_session: AsyncSession) -> None:
    draft = await _seed_builder_draft(db_session, revision=3)
    with pytest.raises(SourceRevisionChangedError):
        await ResumeVersionUseCases().publish_or_resolve(
            db_session,
            PublishResumeVersionCommand(
                source_type="builder_draft",
                draft_id=draft.id,
                source_revision=2,
            ),
        )


async def test_publish_builder_creates_version(db_session: AsyncSession) -> None:
    draft = await _seed_builder_draft(db_session, revision=5)
    result = await ResumeVersionUseCases().publish_or_resolve(
        db_session,
        PublishResumeVersionCommand(
            source_type="builder_draft",
            draft_id=draft.id,
            source_revision=5,
        ),
    )
    assert result.created is True
    assert result.source_revision == 5
    assert result.source_type == "builder_draft"


async def test_publish_builder_idempotent(db_session: AsyncSession) -> None:
    draft = await _seed_builder_draft(db_session, revision=1)
    uc = ResumeVersionUseCases()
    first = await uc.publish_or_resolve(
        db_session,
        PublishResumeVersionCommand(source_type="builder_draft", draft_id=draft.id),
    )
    second = await uc.publish_or_resolve(
        db_session,
        PublishResumeVersionCommand(source_type="builder_draft", draft_id=draft.id),
    )
    assert first.created is True
    assert second.created is False
    assert second.id == first.id


async def test_unknown_source_type_rejected(db_session: AsyncSession) -> None:
    with pytest.raises(SourceNotReadyError):
        await ResumeVersionUseCases().publish_or_resolve(
            db_session,
            PublishResumeVersionCommand(source_type="bogus"),
        )


async def test_privacy_guard_rejects_direct_identifier(db_session: AsyncSession) -> None:
    """A snapshot carrying a real email must be rejected (canary)."""
    resume = ResumeModel(
        id=uuid.uuid4(),
        status="evaluated",
        masked_text="real.email@example.com",
        parsed_result={"profile": {"email": "real.email@example.com"}},
    )
    db_session.add(resume)
    await db_session.commit()
    with pytest.raises(PrivacyRejectedError):
        await ResumeVersionUseCases().publish_or_resolve(
            db_session,
            PublishResumeVersionCommand(source_type="parsed_resume", resume_id=resume.id),
        )


async def test_api_publish_and_get_resume_version(db_session: AsyncSession) -> None:
    from collections.abc import AsyncGenerator

    from backend.infrastructure.db.database import get_db
    from backend.main import app

    resume = await _seed_evaluated_resume(db_session)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/resume-versions",
            json={"source_type": "parsed_resume", "resume_id": str(resume.id)},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["source_type"] == "parsed_resume"
    version_id = data["id"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        detail = await client.get(f"/api/v1/resume-versions/{version_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["masked_snapshot"]["profile"]["name"] == "[MASKED]"
    app.dependency_overrides.clear()


async def test_api_resume_version_not_found(db_session: AsyncSession) -> None:
    from collections.abc import AsyncGenerator

    from backend.infrastructure.db.database import get_db
    from backend.main import app

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/resume-versions/{uuid.uuid4()}")
    assert resp.status_code == 404
    app.dependency_overrides.clear()
