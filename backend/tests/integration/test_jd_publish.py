"""JD version publication tests (RIP-011 #099)."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.jd_publish import (
    JDPublishConflictError,
    JDPublishInvalidError,
    JDPublishUseCases,
    PublishJDCommand,
)
from backend.domain.jd.enums import JDProcessingStep, JDStatus
from backend.infrastructure.db.models import (
    JobDescriptionModel,
)
from backend.tests.conftest import requires_db

pytestmark = requires_db


async def _seed_reviewable_jd(
    session: AsyncSession,
    *,
    review_revision: int = 1,
    title: str = "Backend Engineer",
) -> JobDescriptionModel:
    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title=title,
        raw_text="We need a backend engineer.",
        status=JDStatus.NEEDS_REVIEW.value,
        processing_step=JDProcessingStep.REVIEW.value,
        review_revision=review_revision,
        review_draft={
            "title": title,
            "company": "Acme",
            "department": "Engineering",
            "required_skills": [
                {
                    "key": "s1",
                    "value": "Go",
                    "evidence": "We need Go",
                    "evidence_status": "available",
                    "confidence": 0.9,
                    "provenance": "llm",
                }
            ],
            "responsibilities": [],
            "parser_version": "jd-extractor-v1",
            "model_name": "gpt-4o",
            "schema_version": "jd-review-v1",
        },
    )
    session.add(jd)
    await session.commit()
    await session.refresh(jd)
    return jd


async def test_publish_creates_immutable_version_and_switches_current(
    db_session: AsyncSession,
) -> None:
    jd = await _seed_reviewable_jd(db_session)
    version = await JDPublishUseCases().publish(
        db_session,
        PublishJDCommand(jd_id=jd.id, expected_review_revision=1),
    )
    assert version.version_no == 1
    assert version.schema_version == "jd-review-v1"
    assert version.publication_reason == "user_confirmed"
    await db_session.refresh(jd)
    assert jd.status == JDStatus.READY.value
    assert jd.processing_step == JDProcessingStep.DONE.value
    assert jd.current_version_id == version.id


async def test_publish_is_idempotent(db_session: AsyncSession) -> None:
    jd = await _seed_reviewable_jd(db_session)
    uc = JDPublishUseCases()
    first = await uc.publish(db_session, PublishJDCommand(jd_id=jd.id, expected_review_revision=1))
    second = await uc.publish(db_session, PublishJDCommand(jd_id=jd.id, expected_review_revision=1))
    assert second.id == first.id
    assert second.version_no == first.version_no


async def test_publish_rejects_stale_review_revision(db_session: AsyncSession) -> None:
    jd = await _seed_reviewable_jd(db_session, review_revision=3)
    with pytest.raises(JDPublishConflictError):
        await JDPublishUseCases().publish(
            db_session,
            PublishJDCommand(jd_id=jd.id, expected_review_revision=2),
        )


async def test_publish_rejects_missing_title(db_session: AsyncSession) -> None:
    jd = await _seed_reviewable_jd(db_session, title="")
    with pytest.raises(JDPublishInvalidError):
        await JDPublishUseCases().publish(
            db_session,
            PublishJDCommand(jd_id=jd.id, expected_review_revision=1),
        )


async def test_old_version_unchanged_after_later_publication(db_session: AsyncSession) -> None:
    jd = await _seed_reviewable_jd(db_session, title="First Title")
    uc = JDPublishUseCases()
    v1 = await uc.publish(db_session, PublishJDCommand(jd_id=jd.id, expected_review_revision=1))
    v1_structured = v1.structured

    # Update the draft and publish v2.
    jd.status = JDStatus.NEEDS_REVIEW.value
    jd.review_revision = 2
    jd.review_draft["title"] = "Second Title"
    await db_session.commit()

    v2 = await uc.publish(db_session, PublishJDCommand(jd_id=jd.id, expected_review_revision=2))
    assert v2.version_no == 2
    assert v2.id != v1.id

    # v1 content must be unchanged.
    await db_session.refresh(v1)
    assert v1.structured == v1_structured
    assert v1.structured["title"] == "First Title"


async def test_list_history_returns_latest_first(db_session: AsyncSession) -> None:
    jd = await _seed_reviewable_jd(db_session)
    uc = JDPublishUseCases()
    await uc.publish(db_session, PublishJDCommand(jd_id=jd.id, expected_review_revision=1))
    jd.status = JDStatus.NEEDS_REVIEW.value
    jd.review_revision = 2
    jd.review_draft["title"] = "Second"
    await db_session.commit()
    await uc.publish(db_session, PublishJDCommand(jd_id=jd.id, expected_review_revision=2))

    versions = await uc.list_for_jd(db_session, jd.id)
    assert [v.version_no for v in versions] == [2, 1]


async def test_api_publish_flow(db_session: AsyncSession) -> None:
    from collections.abc import AsyncGenerator

    from backend.infrastructure.db.database import get_db
    from backend.main import app

    jd = await _seed_reviewable_jd(db_session)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/jd/{jd.id}/publish",
            json={"expected_review_revision": 1, "publication_reason": "user_confirmed"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["version_no"] == 1
    app.dependency_overrides.clear()
