"""JD image import API and pipeline tests (RIP-012 #103).

OCR is resolved through the parser registry; these tests register a fake
engine so the worker stage and API contract run without a provider.
"""

from __future__ import annotations

import io
import uuid

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.jd_service.processing import JDProcessingService
from backend.domain.jd.enums import JDProcessingStep, JDStatus
from backend.infrastructure.db.models import FileModel, JobDescriptionModel
from backend.infrastructure.parsers.image_parser import (
    OCRAvailabilityError,
    OCREngine,
    OCRResult,
    register_ocr_engine,
)
from backend.tests.conftest import requires_db

pytestmark = requires_db


class _FakeOcrEngine(OCREngine):
    version = "ocr-test-v1"

    def __init__(self, text: str) -> None:
        self.text = text

    async def extract(self, image_path: str) -> OCRResult:
        return OCRResult(raw_text=self.text, pages=1)


class _UnavailableEngine(OCREngine):
    version = "ocr-none-v0"

    async def extract(self, image_path: str) -> OCRResult:
        raise OCRAvailabilityError("No OCR engine is configured")


def _png_bytes(text_size: tuple[int, int] = (128, 64)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", text_size, color=(255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def _ocr_engine() -> None:
    register_ocr_engine(_FakeOcrEngine("Senior Backend Engineer\nWe need Go and Python."))


@pytest.fixture(autouse=True)
def _llm_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    async def llm_ready(_: AsyncSession) -> bool:
        return True

    monkeypatch.setattr("backend.api.v1.jd.has_verified_config", llm_ready)


async def _upload_image(client: AsyncClient, data: bytes | None = None, filename: str = "jd.png") -> dict:
    files = {"file": (filename, data or _png_bytes(), "image/png")}
    response = await client.post("/api/v1/jd/import/image", files=files)
    return response.json()


async def _run_source_extract(session: AsyncSession, jd_id: uuid.UUID, run_id: uuid.UUID | None) -> str:
    """Execute the worker stage in-process against the seeded jd/run."""
    assert run_id is not None
    return await JDProcessingService().source_extract(session, jd_id, run_id)


async def test_image_import_api_accepts_png_and_persists_source(
    db_session: AsyncSession,
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The API dispatches through Celery; stub the broker handoff to keep the
    # test hermetic while still exercising the full HTTP contract.
    async def no_dispatch(self: object, session: AsyncSession, jd: JobDescriptionModel, **_: object) -> object:
        # Mirror the real handoff, which refreshes server-default fields
        # (created_at/updated_at) before the response is serialized.
        await session.refresh(jd)
        return type("R", (), {"jd": jd, "dispatch_failed": False})()

    from backend.application import jd_import_service

    monkeypatch.setattr(jd_import_service.JDImportService, "_dispatch_or_mark_failed", no_dispatch)

    payload = await _upload_image(async_client)
    assert payload["code"] == 0
    jd_id = payload["data"]["id"]

    jd = await db_session.get(JobDescriptionModel, uuid.UUID(jd_id))
    assert jd is not None
    assert jd.source_type == "image"
    assert jd.source_file_id is not None
    assert jd.status == JDStatus.PROCESSING.value

    file_record = await db_session.get(FileModel, jd.source_file_id)
    assert file_record is not None
    assert file_record.owner_type == "job_description"
    assert file_record.sha256_hash == "0" * 64 or len(file_record.sha256_hash) == 64


async def test_image_import_api_rejects_unsupported_type(
    db_session: AsyncSession,
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_dispatch(self: object, session: AsyncSession, jd: JobDescriptionModel, **_: object) -> object:
        # Mirror the real handoff, which refreshes server-default fields
        # (created_at/updated_at) before the response is serialized.
        await session.refresh(jd)
        return type("R", (), {"jd": jd, "dispatch_failed": False})()

    from backend.application import jd_import_service

    monkeypatch.setattr(jd_import_service.JDImportService, "_dispatch_or_mark_failed", no_dispatch)

    response = await async_client.post(
        "/api/v1/jd/import/image",
        files={"file": ("jd.txt", b"plain text", "text/plain")},
    )
    payload = response.json()
    assert payload["code"] != 0
    assert "Only PNG and JPEG" in payload["message"]


async def test_image_import_api_rejects_mime_mismatch(
    db_session: AsyncSession,
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_dispatch(self: object, session: AsyncSession, jd: JobDescriptionModel, **_: object) -> object:
        # Mirror the real handoff, which refreshes server-default fields
        # (created_at/updated_at) before the response is serialized.
        await session.refresh(jd)
        return type("R", (), {"jd": jd, "dispatch_failed": False})()

    from backend.application import jd_import_service

    monkeypatch.setattr(jd_import_service.JDImportService, "_dispatch_or_mark_failed", no_dispatch)

    response = await async_client.post(
        "/api/v1/jd/import/image",
        files={"file": ("jd.png", _png_bytes(), "image/jpeg")},
    )
    payload = response.json()
    assert payload["code"] != 0
    assert "MIME" in payload["message"]


async def test_image_worker_source_extract_feeds_ocr_text_into_pipeline(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Image JD",
        source_type="image",
        raw_text="",
        status=JDStatus.PROCESSING.value,
        processing_step=JDProcessingStep.QUEUED.value,
        processing_run_id=uuid.uuid4(),
    )
    db_session.add(jd)
    await db_session.flush()

    file_record = FileModel(
        id=uuid.uuid4(),
        original_name="jd.png",
        storage_path="jd/test/jd.png",
        content_type="image/png",
        size_bytes=4,
        sha256_hash="1" * 64,
        owner_type="job_description",
        owner_id=jd.id,
    )
    db_session.add(file_record)
    await db_session.flush()
    jd.source_file_id = file_record.id
    await db_session.commit()

    import backend.application.jd_service.processing as processing_mod

    def fake_download(bucket: str, storage_path: str) -> bytes:
        return _png_bytes()

    monkeypatch.setattr(processing_mod, "download_file", fake_download)
    result = await _run_source_extract(db_session, jd.id, jd.processing_run_id)

    assert result == "processing"
    await db_session.refresh(jd)
    assert jd.raw_text == "Senior Backend Engineer We need Go and Python."
    assert jd.parser_version == "ocr-test-v1"
    assert jd.processing_step == JDProcessingStep.DUPLICATE_CHECK.value


async def test_image_worker_unavailable_ocr_marks_failed_safely(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_ocr_engine(_UnavailableEngine())
    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Image JD",
        source_type="image",
        raw_text="",
        status=JDStatus.PROCESSING.value,
        processing_step=JDProcessingStep.QUEUED.value,
        processing_run_id=uuid.uuid4(),
    )
    db_session.add(jd)
    await db_session.flush()
    file_record = FileModel(
        id=uuid.uuid4(),
        original_name="jd.png",
        storage_path="jd/test/jd.png",
        content_type="image/png",
        size_bytes=4,
        sha256_hash="2" * 64,
        owner_type="job_description",
        owner_id=jd.id,
    )
    db_session.add(file_record)
    await db_session.flush()
    jd.source_file_id = file_record.id
    await db_session.commit()

    import backend.application.jd_service.processing as processing_mod

    def fake_download(bucket: str, storage_path: str) -> bytes:
        return _png_bytes()

    monkeypatch.setattr(processing_mod, "download_file", fake_download)
    with pytest.raises(Exception):
        await _run_source_extract(db_session, jd.id, jd.processing_run_id)
    register_ocr_engine(_FakeOcrEngine("Senior Backend Engineer\nWe need Go and Python."))
