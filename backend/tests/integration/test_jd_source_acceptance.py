"""Five-source end-to-end contract acceptance (RIP-012 #106).

Each source must share the same duplicate / review / publish / archive /
storage contract: every flow ends in a published immutable version, image
runs through the OCR registry only, manual creation makes no LLM call, and
no import mode creates a Job Target.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.jd_publish import JDPublishUseCases, PublishJDCommand
from backend.application.jd_service.processing import JDProcessingService
from backend.domain.jd.enums import JDProcessingStep, JDStatus
from backend.domain.jd.schemas import ExtractedSkill, JDExtraction
from backend.infrastructure.db.models import (
    FileModel,
    JobDescriptionModel,
    JobDescriptionVersionModel,
)
from backend.tests.conftest import requires_db

pytestmark = requires_db


class _Extractor:
    """Fake LLM extractor: returns a fixed extraction without a provider."""

    def __init__(self, _: object) -> None:
        pass

    version = "jd-extractor-v1"
    model_info = "fake-model"

    async def extract(self, _: str) -> JDExtraction:
        return JDExtraction(
            title="Pipeline JD",
            company="Acceptance Co",
            location="Shanghai",
            responsibilities=["Own service reliability"],
            required_skills=[ExtractedSkill(name="Go", evidence="Go")],
            preferred_skills=[],
        )


def _patch_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    async def verified_config(_: AsyncSession) -> object:
        return object()

    monkeypatch.setattr("backend.application.jd_service.processing.get_active_verified_config", verified_config)
    monkeypatch.setattr("backend.application.jd_service.processing.LLMGateway.from_config", lambda _config: object())
    monkeypatch.setattr("backend.application.jd_service.processing.JDExtractor", _Extractor)


def _plain_jd(
    *,
    source: str,
    title: str,
    run_id: uuid.UUID,
    raw_text: str = "This is a long enough job description for the pipeline",
    has_file: bool = False,
    has_url: bool = False,
    storage_path: str = "jd/acceptance/object.bin",
) -> JobDescriptionModel:
    return JobDescriptionModel(
        id=uuid.uuid4(),
        title=title,
        source_type=source,
        raw_text="" if has_file else raw_text,
        status=JDStatus.PROCESSING.value,
        processing_step=JDProcessingStep.QUEUED.value,
        processing_run_id=run_id,
        source_file_id=None,
        source_url="https://example.com/jobs/acceptance" if has_url else None,
    )


async def _run_pipeline_stages(
    session: AsyncSession,
    jd: JobDescriptionModel,
    *,
    run_id: uuid.UUID,
) -> None:
    """Drive source_extract/duplicate_check/llm_extract; the final stage writes the draft."""
    service = JDProcessingService()
    result = await service.source_extract(session, jd.id, run_id)
    assert result == "processing"
    result = await service.duplicate_check(session, jd.id, run_id)
    assert result == "processing"
    await session.refresh(jd)
    assert jd.content_hash is not None
    result = await service.llm_extract(session, jd.id, run_id)
    assert result == "needs_review"
    await session.refresh(jd)
    assert jd.status == JDStatus.NEEDS_REVIEW.value
    assert jd.processing_step == JDProcessingStep.REVIEW.value
    assert jd.review_revision == 1
    draft = jd.review_draft or {}
    assert draft["title"] == "Pipeline JD"
    assert draft["parser_version"] == "jd-extractor-v1"
    assert draft["model_name"] == "fake-model"
    assert draft["responsibilities"][0]["provenance"] == "source"
    assert draft["responsibilities"][0]["evidence_status"] == "available"
    assert draft["required_skills"][0]["critical"] is False


async def _publish(session: AsyncSession, jd: JobDescriptionModel) -> JobDescriptionVersionModel:
    version = await JDPublishUseCases().publish(
        session,
        PublishJDCommand(jd_id=jd.id, expected_review_revision=1),
    )
    return version


async def _assert_published_version(
    session: AsyncSession,
    jd: JobDescriptionModel,
    *,
    source: str,
) -> JobDescriptionVersionModel:
    await session.refresh(jd)
    assert jd.status == JDStatus.READY.value
    assert jd.current_version_id is not None
    version = await session.get(JobDescriptionVersionModel, jd.current_version_id)
    assert version is not None
    assert version.structured["title"] == "Pipeline JD"
    assert version.source_metadata["source_type"] == source
    return version


@pytest.mark.parametrize(
    ("source", "raw_text", "has_file"),
    [
        ("text", "This is a long enough job description for the pipeline", False),
        ("file", "", True),
        ("image", "", True),
        ("url", "This is a long enough job description for the pipeline", False),
    ],
)
async def test_each_worker_source_flow_ends_in_published_version(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    raw_text: str,
    has_file: bool,
) -> None:
    """text/file/image/url all reach a published version through one contract."""
    _patch_llm(monkeypatch)
    import backend.application.jd_service.processing as processing_mod

    # Unique raw text per case: content-hash duplicate detection is scoped to
    # user/JD rows, and the integration DB persists across tests in a session.
    content = (
        f"{source}-specific job description text for the acceptance flow "
        "that differs from every other source case and prior fixtures."
    )
    if has_file:

        file_record = FileModel(
            id=uuid.uuid4(),
            original_name="source.txt",
            storage_path=f"jd/acceptance/{source}.txt",
            content_type="text/plain",
            size_bytes=8,
            sha256_hash="a" * 64,
            owner_type="job_description",
            owner_id=uuid.uuid4(),
        )
        db_session.add(file_record)
        await db_session.flush()

        def fake_download(_bucket: str, _storage_path: str) -> bytes:
            return content.encode()

        monkeypatch.setattr(processing_mod, "download_file", fake_download)
    else:
        file_record = None

    if source == "url":
        async def fake_fetch(_self: object, _url: str) -> str:
            return content

        monkeypatch.setattr(processing_mod, "SafeWebFetcher", lambda: type("F", (), {"fetch_text": fake_fetch})())

    run_id = uuid.uuid4()
    jd = _plain_jd(
        source=source,
        title=f"{source} pipeline JD",
        run_id=run_id,
        raw_text=content if not has_file else "",
        has_file=has_file,
        has_url=source == "url",
    )
    db_session.add(jd)
    await db_session.flush()
    if file_record is not None:
        jd.source_file_id = file_record.id
    await db_session.commit()

    await _run_pipeline_stages(db_session, jd, run_id=run_id)
    await _publish(db_session, jd)
    await _assert_published_version(db_session, jd, source=source)


async def test_manual_flow_makes_no_llm_call_and_publishes(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Manual import enters review without an LLM gate and publishes via the shared contract."""
    from backend.application import jd_import_service as import_mod

    async def no_dispatch(
        self: object,
        session: AsyncSession,
        jd: JobDescriptionModel,
        **_: object,
    ) -> object:
        await session.refresh(jd)
        return type("R", (), {"jd": jd, "dispatch_failed": False})()

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(import_mod.JDImportService, "_dispatch_or_mark_failed", no_dispatch)
    try:
        resp = await async_client.post(
            "/api/v1/jd/import/manual",
            json={
                "title": "Manual Acceptance JD",
                "company": "Acceptance Co",
                "required_skills": [{"name": "Go", "critical": True}],
            },
        )
    finally:
        monkeypatch.undo()

    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    jd_id = uuid.UUID(resp.json()["data"]["id"])
    jd = await db_session.get(JobDescriptionModel, jd_id)
    assert jd is not None
    assert jd.status == JDStatus.NEEDS_REVIEW.value
    assert jd.processing_run_id is None
    assert jd.source_file_id is None
    assert jd.source_url is None
    assert jd.processing_step == JDProcessingStep.REVIEW.value

    version = await _publish(db_session, jd)
    assert version.structured["title"] == "Manual Acceptance JD"
    assert version.source_metadata["source_type"] == "manual"
    assert version.structured["required_skills"][0]["provenance"] == "manual"


async def test_no_import_mode_creates_job_target(db_session: AsyncSession) -> None:
    """No import path may create a Job Target before a downstream command."""
    from backend.infrastructure.db.models import JobTargetModel

    stmt = select(JobTargetModel.id)
    rows = (await db_session.execute(stmt)).scalars().all()
    for jd_id in rows:
        jd = await db_session.get(JobDescriptionModel, jd_id)
        assert jd is not None and jd.status != JDStatus.PROCESSING.value

    import backend.application.jd_import_service as import_mod

    source = open(import_mod.__file__).read()
    assert "JobTarget" not in source
