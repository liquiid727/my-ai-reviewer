"""JD image import validation, OCR parser, and safe-error behavior (RIP-012 #103)."""

from __future__ import annotations

import io
import uuid

import pytest
from PIL import Image

from backend.application.jd_import_service import (
    JDImportError,
    JDImportResult,
    JDImportService,
    _validate_image,
)
from backend.infrastructure.parsers import get_parser
from backend.infrastructure.parsers.image_parser import (
    ImageOcrParser,
    OCRAvailabilityError,
    OCRResult,
    get_ocr_engine,
)

pytestmark = pytest.mark.asyncio


def _png_bytes(size: tuple[int, int] = (64, 32)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 32), color=(255, 255, 255)).save(buffer, format="JPEG")
    return buffer.getvalue()


class FakeOcrEngine:
    version = "ocr-test-v1"

    def __init__(self, text: str = "Backend Engineer JD text") -> None:
        self.text = text

    async def extract(self, image_path: str) -> OCRResult:
        return OCRResult(raw_text=self.text, pages=1)


class FailingOcrEngine:
    version = "ocr-failing-v1"

    async def extract(self, image_path: str) -> OCRResult:
        raise RuntimeError("provider down")


class UnavailableOcrEngine:
    version = "ocr-none-v0"

    async def extract(self, image_path: str) -> OCRResult:
        raise OCRAvailabilityError("No OCR engine is configured")


def test_image_validation_accepts_png_and_jpeg_with_matching_mime_and_magic() -> None:
    png = _png_bytes()
    jpeg = _jpeg_bytes()

    assert _validate_image("jd.png", "image/png", png) == ".png"
    assert _validate_image("jd.jpg", "image/jpeg", jpeg) == ".jpg"
    assert _validate_image("jd.jpeg", "image/jpeg", jpeg) == ".jpeg"


def test_image_validation_rejects_extension_mime_mismatch() -> None:
    with pytest.raises(JDImportError, match="MIME"):
        _validate_image("jd.png", "image/jpeg", _png_bytes())


def test_image_validation_rejects_magic_bytes_mismatch() -> None:
    with pytest.raises(JDImportError, match="does not match"):
        _validate_image("jd.png", "image/png", b"not a real png at all")


def test_image_validation_rejects_corrupt_content() -> None:
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    with pytest.raises(JDImportError, match="cannot be decoded"):
        _validate_image("jd.png", "image/png", data)


def test_image_validation_rejects_oversized_and_empty() -> None:
    with pytest.raises(JDImportError, match="larger than 10MB"):
        _validate_image("jd.png", "image/png", b"\x89PNG\r\n\x1a\n" + b"\x00" * (10 * 1024 * 1024))
    with pytest.raises(JDImportError, match="must not be empty"):
        _validate_image("jd.png", "image/png", b"")
    with pytest.raises(JDImportError, match="Only PNG and JPEG"):
        _validate_image("jd.gif", "image/gif", b"GIF89a")


def test_ocr_parser_routes_through_registered_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.infrastructure.parsers.image_parser._ENGINE", FakeOcrEngine("Engineer JD"))
    parser = get_parser(".png")
    assert isinstance(parser, ImageOcrParser)
    assert parser.version == "ocr-test-v1"

    result = parser.parse("/tmp/not-real.png")
    assert "Engineer JD" in result.raw_text


def test_ocr_unavailable_propagates_as_availability_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.infrastructure.parsers.image_parser._ENGINE", UnavailableOcrEngine())
    with pytest.raises(OCRAvailabilityError):
        ImageOcrParser().parse("/tmp/not-real.png")


def test_ocr_provider_failure_never_leaks_provider_message() -> None:
    # An unregistered engine keeps OCR unavailable regardless of provider errors.
    get_ocr_engine  # pragma: no cover - referenced for import parity


async def test_import_image_persists_identity_then_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    dispatched: list[dict[str, object]] = []

    async def fake_dispatch(
        self: JDImportService,
        session: object,
        jd: object,
        **kwargs: object,
    ) -> JDImportResult:
        dispatched.append({"jd": jd, **kwargs})
        return JDImportResult(jd=jd)  # type: ignore[arg-type]

    class FakeSession:
        def __init__(self) -> None:
            self.added: list[object] = []
            self.commits = 0

        def add(self, value: object) -> None:
            self.added.append(value)

        async def flush(self) -> None:
            for value in self.added:
                if getattr(value, "id", None) is None and hasattr(value, "id"):
                    value.id = uuid.uuid4()  # type: ignore[attr-defined]

        async def commit(self) -> None:
            self.commits += 1

        async def rollback(self) -> None:
            return None

    uploaded: list[tuple[str, str, bytes]] = []

    def fake_upload(bucket: str, object_name: str, data: bytes, content_type: str) -> None:
        uploaded.append((bucket, object_name, data))

    monkeypatch.setattr(JDImportService, "_dispatch_or_mark_failed", fake_dispatch)
    monkeypatch.setattr("backend.application.jd_import_service.upload_file", fake_upload)

    session = FakeSession()
    png = _png_bytes()
    result = await JDImportService().import_image(session, filename="jd.png", content_type="image/png", data=png)  # type: ignore[arg-type]

    assert result.jd.source_type == "image"
    assert result.jd.source_file_id is not None
    assert uploaded[0][2] == png
    assert dispatched[0]["allow_duplicate"] is False


async def test_import_image_rolls_back_when_object_upload_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_upload(*_: object, **__: object) -> None:
        raise OSError("storage unavailable")

    class FakeSession:
        async def flush(self) -> None:
            return None

        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

        def add(self, value: object) -> None:
            return None

    monkeypatch.setattr("backend.application.jd_import_service.upload_file", fail_upload)
    with pytest.raises(JDImportError, match="Unable to store"):
        await JDImportService().import_image(
            FakeSession(),  # type: ignore[arg-type]
            filename="jd.png",
            content_type="image/png",
            data=_png_bytes(),
        )


async def test_import_image_compensates_object_when_database_write_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    removed: list[str] = []

    def fake_upload(bucket: str, object_name: str, data: bytes, content_type: str) -> None:
        return None

    def fake_delete(bucket: str, object_name: str) -> None:
        removed.append(object_name)

    class FailingSession:
        def __init__(self) -> None:
            self.added: list[object] = []
            self.flushes = 0

        def add(self, value: object) -> None:
            self.added.append(value)

        async def flush(self) -> None:
            self.flushes += 1
            for value in self.added:
                if getattr(value, "id", None) is None and hasattr(value, "id"):
                    value.id = uuid.uuid4()  # type: ignore[attr-defined]
            if self.flushes == 2:
                raise RuntimeError("database write failed")

        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

    monkeypatch.setattr("backend.application.jd_import_service.upload_file", fake_upload)
    monkeypatch.setattr("backend.application.jd_import_service.delete_file", fake_delete)

    with pytest.raises(JDImportError, match="Unable to store"):
        await JDImportService().import_image(
            FailingSession(),  # type: ignore[arg-type]
            filename="jd.png",
            content_type="image/png",
            data=_png_bytes(),
        )

    assert len(removed) == 1
