"""JD review-draft workflow tests (RIP-011 #098)."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.jd_review_draft import (
    JDReviewConflictError,
    JDReviewDraftUseCases,
    JDReviewFinalizeError,
    JDReviewNotInReviewError,
)
from backend.domain.jd.enums import JDProcessingStep, JDStatus
from backend.domain.jd.schemas import DraftItem, ReviewDraft
from backend.infrastructure.db.models import JobDescriptionModel
from backend.tests.conftest import requires_db

pytestmark = requires_db


async def _seed_jd(
    session: AsyncSession,
    *,
    status: str = "needs_review",
    step: str = "review",
    run_id: uuid.UUID | None = None,
) -> JobDescriptionModel:
    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Review JD",
        raw_text="JD",
        status=status,
        processing_step=step,
        processing_run_id=run_id,
        review_revision=1,
        review_draft={
            "title": "Review JD",
            "responsibilities": [
                {
                    "key": "r1",
                    "value": "Build services",
                    "evidence_status": "available",
                    "confidence": 0.9,
                    "provenance": "llm",
                }
            ],
        },
    )
    session.add(jd)
    await session.commit()
    await session.refresh(jd)
    return jd


def _draft() -> ReviewDraft:
    return ReviewDraft(
        title="Review JD",
        responsibilities=[
            DraftItem(
                key="r1",
                value="Build services and APIs",
                evidence="Build services",
                evidence_status="available",
                confidence=0.9,
                provenance="llm",
            )
        ],
    )


async def test_save_review_draft_marks_manual_provenance(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session)
    result = await JDReviewDraftUseCases().save_review_draft(
        db_session,
        jd.id,
        expected_review_revision=1,
        draft=_draft(),
    )
    assert result["review_revision"] == 2
    # The changed responsibility value is now manual.
    items = result["draft"]["responsibilities"]
    assert items[0]["provenance"] == "manual"


async def test_save_review_draft_conflict(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session)
    with pytest.raises(JDReviewConflictError):
        await JDReviewDraftUseCases().save_review_draft(
            db_session,
            jd.id,
            expected_review_revision=99,
            draft=_draft(),
        )


async def test_save_review_draft_not_reviewable(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session, status="ready", step="done")
    with pytest.raises(JDReviewNotInReviewError):
        await JDReviewDraftUseCases().save_review_draft(
            db_session,
            jd.id,
            expected_review_revision=1,
            draft=_draft(),
        )


async def test_finalize_requires_run_ownership(db_session: AsyncSession) -> None:
    jd = await _seed_jd(db_session, status="processing", step="structure_parse", run_id=uuid.uuid4())
    with pytest.raises(JDReviewFinalizeError):
        await JDReviewDraftUseCases().finalize_draft_from_run(
            db_session,
            jd.id,
            run_id=uuid.uuid4(),  # wrong run
            draft=_draft(),
        )


async def test_finalize_success_enters_needs_review(db_session: AsyncSession) -> None:
    run_id = uuid.uuid4()
    jd = await _seed_jd(db_session, status="processing", step="structure_parse", run_id=run_id)
    ok = await JDReviewDraftUseCases().finalize_draft_from_run(
        db_session,
        jd.id,
        run_id=run_id,
        draft=_draft(),
    )
    assert ok is True
    await db_session.refresh(jd)
    assert jd.status == JDStatus.NEEDS_REVIEW.value
    assert jd.processing_step == JDProcessingStep.REVIEW.value


async def test_get_review_draft_exposes_current_version_separately(
    db_session: AsyncSession,
) -> None:
    jd = await _seed_jd(db_session)
    info = await JDReviewDraftUseCases().get_review_draft(db_session, jd.id)
    assert info is not None
    assert info["has_current_version"] is False  # no version published yet
    assert info["review_revision"] == 1


async def test_api_patch_review(db_session: AsyncSession) -> None:
    from collections.abc import AsyncGenerator

    from backend.infrastructure.db.database import get_db
    from backend.main import app

    jd = await _seed_jd(db_session)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/jd/{jd.id}/review",
            json={
                "expected_review_revision": 1,
                "draft": {
                    "title": "Review JD",
                    "responsibilities": [
                        {
                            "key": "r1",
                            "value": "Build services and APIs",
                            "evidence_status": "available",
                            "confidence": 0.9,
                            "provenance": "llm",
                        }
                    ],
                },
            },
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["review_revision"] == 2
    app.dependency_overrides.clear()


async def test_api_patch_review_conflict(db_session: AsyncSession) -> None:
    from collections.abc import AsyncGenerator

    from backend.infrastructure.db.database import get_db
    from backend.main import app

    jd = await _seed_jd(db_session)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/jd/{jd.id}/review",
            json={
                "expected_review_revision": 99,
                "draft": {"title": "Review JD", "responsibilities": []},
            },
        )
    assert resp.status_code == 200  # APIResponse envelope; conflict surfaces in code
    assert resp.json()["code"] == 409
    app.dependency_overrides.clear()
