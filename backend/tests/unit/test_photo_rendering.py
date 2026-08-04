"""照片渲染集成逻辑单测 —— draft_photo_data_uri 与 PDF 导出照片透传（免数据库）。"""

import base64
import uuid
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.resume_builder import services
from backend.domain.resume_builder.enums import LayoutDensity
from backend.domain.resume_builder.schemas import ExportOptions, LayoutPolicy, ResumeDraft
from backend.infrastructure.db.models import ResumeDraftModel


def _draft(identity: dict[str, Any] | None = None) -> ResumeDraft:
    return ResumeDraft(title="测试简历", identity=identity or {})


class _FakeDraftModel:
    """模拟 ResumeDraftModel（免数据库）。"""

    def __init__(self, identity: dict[str, Any]) -> None:
        self.id = uuid.uuid4()
        self.title = "测试简历"
        self.content: dict[str, Any] = {"identity": identity, "summary": None, "sections": []}
        self.template_id = "classic"
        self.design_tokens = None
        self.layout_mode = "auto_pages"
        self.target_page_count = None


class _FakeSession:
    """充当 AsyncSession（仅需 commit/refresh 空实现）。"""

    async def commit(self) -> None:
        pass

    async def refresh(self, model: Any) -> None:
        pass


def _session() -> AsyncSession:
    return cast(AsyncSession, _FakeSession())


def _as_draft(model: _FakeDraftModel) -> ResumeDraftModel:
    return cast(ResumeDraftModel, model)


class TestUpdateDraftPhotoGuard:
    """update_draft 不得绕过 confirm 归属校验直写 identity.photo。"""

    async def test_client_photo_stripped_and_existing_preserved(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Client photo stripped; confirmed existing photo retained; name masked."""
        model = _FakeDraftModel({"name": "张三", "photo": "d1/processed-legit.png"})

        async def fake_get_draft(session: Any, draft_id: Any) -> Any:
            return model

        monkeypatch.setattr(services, "get_draft", fake_get_draft)
        await services.update_draft(
            _session(),
            model.id,
            {"identity": {"name": "李四", "photo": "other-draft/processed-stolen.png"}},
        )

        identity = cast(dict[str, Any], model.content["identity"])
        assert str(identity["name"]).startswith("[[PERSON_")
        # Confirmed photo must survive identity patches (only set_draft_photo mutates it).
        assert identity["photo"] == "d1/processed-legit.png"
        assert identity["photo"] != "other-draft/processed-stolen.png"

    async def test_client_photo_stripped_when_no_existing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Client photo stripped when draft had no confirmed photo."""
        model = _FakeDraftModel({"name": "张三"})

        async def fake_get_draft(session: Any, draft_id: Any) -> Any:
            return model

        monkeypatch.setattr(services, "get_draft", fake_get_draft)
        await services.update_draft(
            _session(),
            model.id,
            {"identity": {"name": "李四", "photo": "other-draft/processed-x.png"}},
        )

        identity = cast(dict[str, Any], model.content["identity"])
        assert "photo" not in identity


class TestDraftPhotoDataUri:
    """draft_photo_data_uri：无照片 / 有照片 / 读取失败三路径。"""

    def test_no_photo_returns_none(self) -> None:
        assert services.draft_photo_data_uri(_draft()) is None
        assert services.draft_photo_data_uri(_draft({"name": "张三"})) is None

    def test_photo_encoded_as_data_uri(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(services, "download_file", lambda bucket, obj: b"png-bytes")
        uri = services.draft_photo_data_uri(_draft({"photo": "d1/processed-x.png"}))
        expected = base64.b64encode(b"png-bytes").decode("ascii")
        assert uri == f"data:image/png;base64,{expected}"

    def test_download_failure_degrades_to_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def raise_error(bucket: str, obj: str) -> bytes:
            raise RuntimeError("minio down")

        monkeypatch.setattr(services, "download_file", raise_error)
        assert services.draft_photo_data_uri(_draft({"photo": "d1/processed-x.png"})) is None


class TestExportWithPhoto:
    """export_draft_pdf：RIP-009 request-scoped photo only — no silent MinIO rehydrate."""

    async def test_export_does_not_auto_inject_persisted_identity_photo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Persisted identity.photo must NOT be auto-loaded from MinIO on export.

        RIP-009: export photos are request-scoped transient only. Callers pass
        photo_data_uri explicitly; export_draft_pdf must not silently rehydrate
        from storage even when identity.photo is present and downloadable.
        """
        captured: dict[str, Any] = {}
        download_calls: list[tuple[str, str]] = []

        class _FakePdfRenderer:
            async def render_pdf(
                self,
                draft: ResumeDraft,
                layout_policy: LayoutPolicy | None = None,
                photo_data_uri: str | None = None,
            ) -> tuple[bytes, int, bool, LayoutDensity]:
                captured["photo_data_uri"] = photo_data_uri
                return b"pdf", 1, True, LayoutDensity.NORMAL

        def track_download(bucket: str, obj: str) -> bytes:
            download_calls.append((bucket, obj))
            return b"png-bytes"

        monkeypatch.setattr(services, "PdfRenderer", _FakePdfRenderer)
        monkeypatch.setattr(services, "download_file", track_download)

        model = _FakeDraftModel({"name": "[[PERSON_01]]", "photo": "d1/processed-x.png"})
        pdf_bytes, _result = await services.export_draft_pdf(
            cast(AsyncSession, None),
            _as_draft(model),
            ExportOptions(persist=False),
        )

        assert pdf_bytes == b"pdf"
        assert captured["photo_data_uri"] is None
        assert download_calls == [], "export must not silently load identity.photo from MinIO"

    async def test_export_without_photo_passes_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}

        class _FakePdfRenderer:
            async def render_pdf(
                self,
                draft: ResumeDraft,
                layout_policy: LayoutPolicy | None = None,
                photo_data_uri: str | None = None,
            ) -> tuple[bytes, int, bool, LayoutDensity]:
                captured["photo_data_uri"] = photo_data_uri
                return b"pdf", 1, True, LayoutDensity.NORMAL

        monkeypatch.setattr(services, "PdfRenderer", _FakePdfRenderer)

        model = _FakeDraftModel({"name": "[[PERSON_01]]"})
        await services.export_draft_pdf(cast(AsyncSession, None), _as_draft(model), ExportOptions(persist=False))

        assert captured["photo_data_uri"] is None

    async def test_transient_photo_data_uri_is_forwarded_without_storage(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Explicit request-scoped photo_data_uri is forwarded; storage untouched."""
        captured: dict[str, Any] = {}
        download_calls: list[tuple[str, str]] = []

        class _FakePdfRenderer:
            async def render_pdf(
                self,
                draft: ResumeDraft,
                layout_policy: LayoutPolicy | None = None,
                photo_data_uri: str | None = None,
            ) -> tuple[bytes, int, bool, LayoutDensity]:
                captured["photo_data_uri"] = photo_data_uri
                return b"pdf", 1, True, LayoutDensity.NORMAL

        def track_download(bucket: str, obj: str) -> bytes:
            download_calls.append((bucket, obj))
            return b"png-bytes"

        monkeypatch.setattr(services, "PdfRenderer", _FakePdfRenderer)
        monkeypatch.setattr(services, "download_file", track_download)
        model = _FakeDraftModel({"name": "[[PERSON_01]]", "photo": "d1/processed-x.png"})
        await services.export_draft_pdf(
            cast(AsyncSession, None),
            _as_draft(model),
            ExportOptions(persist=False),
            "data:image/png;base64,abc",
        )
        assert captured["photo_data_uri"] == "data:image/png;base64,abc"
        assert download_calls == [], "transient photo must not touch MinIO"
