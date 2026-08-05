"""Manual JD source creation API tests (RIP-012 #104)."""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.jd_publish import JDPublishUseCases, PublishJDCommand
from backend.domain.jd.enums import JDProcessingStep, JDStatus
from backend.infrastructure.db.models import JobDescriptionModel
from backend.tests.conftest import requires_db

pytestmark = requires_db

MANUAL_PAYLOAD = {
    "title": "Senior Backend Engineer",
    "company": "Example Co",
    "location": "Remote",
    "department": "Platform",
    "responsibilities": ["Own service reliability"],
    "required_skills": [{"name": "Go", "critical": True}, {"name": "PostgreSQL"}],
    "preferred_skills": [{"name": "Kubernetes"}],
    "notes": "Referral",
}


def _payload(*, title: str, **overrides: object) -> dict[str, object]:
    """Base payload with a unique title so canonical hashes never collide

    across tests (rows persist until the session ends; fixtures only roll back).
    """
    return {**MANUAL_PAYLOAD, "title": title, **overrides}


async def test_api_manual_import_creates_review_jd(async_client: AsyncClient, db_session: AsyncSession) -> None:
    resp = await async_client.post("/api/v1/jd/import/manual", json=_payload(title="Manual Review JD"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0

    data = body["data"]
    assert data["source_type"] == "manual"
    assert data["status"] == JDStatus.NEEDS_REVIEW.value
    assert data["title"] == "Manual Review JD"
    assert data["company"] == "Example Co"
    assert data["location"] == "Remote"

    jd = await db_session.get(JobDescriptionModel, uuid.UUID(data["id"]))
    assert jd is not None
    assert jd.review_revision == 1
    assert jd.processing_step == JDProcessingStep.REVIEW.value
    assert jd.processing_run_id is None
    assert jd.extraction_source == "manual"
    assert jd.field_sources == {"title": "manual", "company": "manual"}
    assert jd.content_hash is not None


async def test_api_manual_import_does_not_require_llm(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """Manual import must succeed even with no verified LLM config."""
    resp = await async_client.post("/api/v1/jd/import/manual", json=_payload(title="Manual No LLM"))
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


async def test_api_manual_import_rejects_invalid_payload(async_client: AsyncClient) -> None:
    resp = await async_client.post("/api/v1/jd/import/manual", json={"title": ""})
    assert resp.status_code == 422

    resp = await async_client.post(
        "/api/v1/jd/import/manual",
        json={"title": "Role", "employment_type": "unknown"},
    )
    assert resp.status_code == 422

    resp = await async_client.post(
        "/api/v1/jd/import/manual",
        json={"title": "Role", "required_skills": [{"name": ""}]},
    )
    assert resp.status_code == 422


async def test_manual_duplicate_content_hash_detected(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    first = await async_client.post("/api/v1/jd/import/manual", json=_payload(title="Manual Duplicate A"))
    assert first.status_code == 200
    first_id = uuid.UUID(first.json()["data"]["id"])

    # Whitespace-only differences normalize to the same canonical text, so the
    # second entry is a duplicate and enters duplicate_pending inline.
    shifted = _payload(
        title="Manual Duplicate A",
        company="Example Co  ",
        responsibilities=["Own service reliability "],
    )
    second = await async_client.post("/api/v1/jd/import/manual", json=shifted)
    assert second.status_code == 200
    second_body = second.json()["data"]
    assert second_body["status"] == JDStatus.DUPLICATE_PENDING.value
    second_id = uuid.UUID(second_body["id"])
    assert second_id != first_id

    stmt = select(JobDescriptionModel).where(JobDescriptionModel.id.in_([first_id, second_id]))
    rows = (await db_session.execute(stmt)).scalars().all()
    by_id = {row.id: row for row in rows}
    assert by_id[first_id].content_hash == by_id[second_id].content_hash
    assert by_id[second_id].duplicate_of_id == first_id
    first_hash = by_id[first_id].content_hash
    assert first_hash is not None
    assert len(first_hash) == 64

    # Clean up both rows so later tests do not collide on the canonical hash.
    for jd_id in (first_id, second_id):
        deleted = await async_client.delete(f"/api/v1/jd/{jd_id}")
        assert deleted.status_code == 200


async def test_manual_allow_duplicate_passes_through(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    first = await async_client.post("/api/v1/jd/import/manual", json=_payload(title="Manual Duplicate B"))
    assert first.status_code == 200
    first_id = uuid.UUID(first.json()["data"]["id"])

    second = await async_client.post(
        "/api/v1/jd/import/manual",
        json=_payload(title="Manual Duplicate B", allow_duplicate=True),
    )
    assert second.status_code == 200
    assert second.json()["data"]["status"] == JDStatus.NEEDS_REVIEW.value

    for jd_id in (first_id, uuid.UUID(second.json()["data"]["id"])):
        deleted = await async_client.delete(f"/api/v1/jd/{jd_id}")
        assert deleted.status_code == 200


async def test_manual_jd_publishes_through_version_lifecycle(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    resp = await async_client.post("/api/v1/jd/import/manual", json=_payload(title="Manual Publish Flow"))
    assert resp.status_code == 200
    jd_id = uuid.UUID(resp.json()["data"]["id"])

    version = await JDPublishUseCases().publish(
        db_session,
        PublishJDCommand(jd_id=jd_id, expected_review_revision=1),
    )
    assert version.version_no == 1
    assert version.structured["title"] == "Manual Publish Flow"
    assert version.structured["company"] == "Example Co"
    assert version.structured["department"] == "Platform"
    assert version.structured["location"] == "Remote"

    required = version.structured["required_skills"]
    assert [item["value"] for item in required] == ["Go", "PostgreSQL"]
    go = next(item for item in required if item["value"] == "Go")
    assert go["critical"] is True
    assert go["provenance"] == "manual"
    assert go["evidence_status"] == "unavailable"

    assert version.structured["responsibilities"][0]["value"] == "Own service reliability"
    assert version.structured["responsibilities"][0]["provenance"] == "manual"
    assert version.source_metadata["source_type"] == "manual"
    assert version.source_metadata["generator"]["parser_version"] is None

    jd = await db_session.get(JobDescriptionModel, jd_id)
    assert jd is not None
    assert jd.status == JDStatus.READY.value
    assert jd.current_version_id == version.id
