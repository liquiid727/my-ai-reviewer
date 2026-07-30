"""照片渲染集成逻辑单测 —— draft_photo_data_uri 与 PDF 导出照片透传（免数据库）。"""

import base64
import uuid
from typing import Any

import pytest

from backend.domain.resume_builder import services
from backend.domain.resume_builder.schemas import ExportOptions, ResumeDraft


def _draft(identity: dict[str, Any] | None = None) -> ResumeDraft:
    return ResumeDraft(title="测试简历", identity=identity or {})


class _FakeDraftModel:
    """模拟 ResumeDraftModel（免数据库）。"""

    def __init__(self, identity: dict[str, Any]) -> None:
        self.id = uuid.uuid4()
        self.title = "测试简历"
        self.content = {"identity": identity, "summary": None, "sections": []}
        self.template_id = "classic"
        self.design_tokens = None


class _FakeSession:
    """充当 AsyncSession（仅需 commit/refresh 空实现）。"""

    async def commit(self) -> None:
        pass

    async def refresh(self, model: Any) -> None:
        pass


class TestUpdateDraftPhotoGuard:
    """update_draft 不得绕过 confirm 归属校验直写 identity.photo。"""

    async def test_client_photo_stripped_and_existing_preserved(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        model = _FakeDraftModel({"name": "张三", "photo": "d1/processed-legit.png"})

        async def fake_get_draft(session: Any, draft_id: Any) -> Any:
            return model

        monkeypatch.setattr(services, "get_draft", fake_get_draft)
        await services.update_draft(
            _FakeSession(), model.id,  # type: ignore[arg-type]
            {"identity": {"name": "李四", "photo": "other-draft/processed-stolen.png"}},
        )

        identity = model.content["identity"]
        assert identity["name"] == "李四"
        # 客户端伪造的 photo 被丢弃，已 confirm 的值保留
        assert identity["photo"] == "d1/processed-legit.png"

    async def test_client_photo_stripped_when_no_existing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        model = _FakeDraftModel({"name": "张三"})

        async def fake_get_draft(session: Any, draft_id: Any) -> Any:
            return model

        monkeypatch.setattr(services, "get_draft", fake_get_draft)
        await services.update_draft(
            _FakeSession(), model.id,  # type: ignore[arg-type]
            {"identity": {"name": "李四", "photo": "other-draft/processed-x.png"}},
        )

        assert "photo" not in model.content["identity"]


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
    """export_draft_pdf：照片经 data URI 透传给 PdfRenderer。"""

    async def test_photo_data_uri_passed_to_pdf_renderer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, Any] = {}

        class _FakePdfRenderer:
            async def render_pdf(
                self,
                draft: ResumeDraft,
                auto_one_page: bool = False,
                photo_data_uri: str | None = None,
            ) -> tuple[bytes, int, bool]:
                captured["photo_data_uri"] = photo_data_uri
                return b"pdf", 1, False

        monkeypatch.setattr(services, "PdfRenderer", _FakePdfRenderer)
        monkeypatch.setattr(services, "download_file", lambda bucket, obj: b"png-bytes")

        model = _FakeDraftModel({"name": "张三", "photo": "d1/processed-x.png"})
        pdf_bytes, result = await services.export_draft_pdf(
            None, model, ExportOptions(persist=False),  # type: ignore[arg-type]
        )

        assert pdf_bytes == b"pdf"
        expected = base64.b64encode(b"png-bytes").decode("ascii")
        assert captured["photo_data_uri"] == f"data:image/png;base64,{expected}"

    async def test_export_without_photo_passes_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, Any] = {}

        class _FakePdfRenderer:
            async def render_pdf(
                self,
                draft: ResumeDraft,
                auto_one_page: bool = False,
                photo_data_uri: str | None = None,
            ) -> tuple[bytes, int, bool]:
                captured["photo_data_uri"] = photo_data_uri
                return b"pdf", 1, False

        monkeypatch.setattr(services, "PdfRenderer", _FakePdfRenderer)

        model = _FakeDraftModel({"name": "张三"})
        await services.export_draft_pdf(None, model, ExportOptions(persist=False))  # type: ignore[arg-type]

        assert captured["photo_data_uri"] is None
