"""照片 API 端点单测 —— 上传 / 确认 / 删除 / 400 / 422 / 501 六路径（免数据库）。

直接调用端点函数，monkeypatch 掉 services / MinIO / process_photo 依赖。
"""

import io
import uuid
from typing import Any, cast

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers

from backend.api.v1 import resume_builder as api
from backend.infrastructure.imaging import (
    FaceNotFoundError,
    ImageDecodeError,
    ImagingNotAvailableError,
    ProcessedPhoto,
)

DRAFT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class _FakeSession:
    """充当 AsyncSession 占位（端点内不直接使用其方法）。"""


def _session() -> AsyncSession:
    return cast(AsyncSession, _FakeSession())


def _upload_file(data: bytes, content_type: str = "image/jpeg", filename: str = "me.jpg") -> UploadFile:
    return UploadFile(
        file=io.BytesIO(data),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@pytest.fixture
def patched(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """打桩草稿服务与 MinIO；返回记录字典供断言。"""
    calls: dict[str, Any] = {"uploaded": [], "photo_set": []}

    async def fake_get_draft(session: Any, draft_id: uuid.UUID) -> Any:
        return object()

    async def fake_set_draft_photo(session: Any, draft_id: uuid.UUID, object_name: str | None) -> Any:
        calls["photo_set"].append(object_name)
        return object()

    monkeypatch.setattr(api.services, "get_draft", fake_get_draft)
    monkeypatch.setattr(api.services, "set_draft_photo", fake_set_draft_photo)
    monkeypatch.setattr(api, "_serialize_draft", lambda model: {"draft_id": str(DRAFT_ID)})
    monkeypatch.setattr(api, "ensure_bucket", lambda bucket: None)
    monkeypatch.setattr(api, "object_exists", lambda bucket, object_name: True)
    monkeypatch.setattr(
        api,
        "upload_file",
        lambda bucket, object_name, data, content_type: calls["uploaded"].append(object_name),
    )
    monkeypatch.setattr(api, "presigned_url", lambda bucket, object_name: f"https://minio/{object_name}")
    return calls


class TestUploadPhoto:
    """POST /{draft_id}/photo。"""

    async def test_success(self, patched: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
        """成功路径：处理 → 原图/结果落 MinIO → 返回预览元信息。"""
        monkeypatch.setattr(
            api,
            "process_photo",
            lambda data, bg_color: ProcessedPhoto(b"png-bytes", background_replaced=True),
        )

        resp = await api.upload_photo(DRAFT_ID, _upload_file(b"jpegdata"), "blue", _session())

        assert resp.code == 0
        data = resp.data
        assert data["background_replaced"] is True
        assert data["degraded_reason"] is None
        assert data["bg_color"] == "blue"
        assert data["original_object"].startswith(f"{DRAFT_ID}/original-")
        assert data["processed_object"].startswith(f"{DRAFT_ID}/processed-")
        assert data["processed_url"].startswith("https://minio/")
        assert len(patched["uploaded"]) == 2  # 原图 + 结果

    async def test_degraded_result_passthrough(self, patched: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
        """降级结果透传 degraded_reason（HTTP 200）。"""
        monkeypatch.setattr(
            api,
            "process_photo",
            lambda data, bg_color: ProcessedPhoto(b"png", background_replaced=False, degraded_reason="抠图失败"),
        )

        resp = await api.upload_photo(DRAFT_ID, _upload_file(b"x"), "white", _session())

        assert resp.data["background_replaced"] is False
        assert resp.data["degraded_reason"] == "抠图失败"

    async def test_invalid_content_type_400(self, patched: dict[str, Any]) -> None:
        """非 jpg/png → 400 INVALID_PHOTO。"""
        with pytest.raises(HTTPException) as exc:
            await api.upload_photo(DRAFT_ID, _upload_file(b"x", "image/gif", "a.gif"), "white", _session())
        assert exc.value.status_code == 400
        assert exc.value.detail == "INVALID_PHOTO"

    async def test_oversize_400(self, patched: dict[str, Any]) -> None:
        """超过 10MB → 400 INVALID_PHOTO。"""
        big = b"0" * (api.PHOTO_MAX_SIZE + 1)
        with pytest.raises(HTTPException) as exc:
            await api.upload_photo(DRAFT_ID, _upload_file(big), "white", _session())
        assert exc.value.status_code == 400
        assert exc.value.detail == "INVALID_PHOTO"

    async def test_invalid_bg_color_400(self, patched: dict[str, Any]) -> None:
        """非法背景色 → 400 INVALID_PHOTO。"""
        with pytest.raises(HTTPException) as exc:
            await api.upload_photo(DRAFT_ID, _upload_file(b"x"), "green", _session())
        assert exc.value.status_code == 400

    async def test_no_face_422(self, patched: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
        """未检测到人脸 → 422 FACE_NOT_FOUND。"""

        def raise_no_face(data: bytes, bg_color: str) -> ProcessedPhoto:
            raise FaceNotFoundError("no face")

        monkeypatch.setattr(api, "process_photo", raise_no_face)
        with pytest.raises(HTTPException) as exc:
            await api.upload_photo(DRAFT_ID, _upload_file(b"x"), "white", _session())
        assert exc.value.status_code == 422
        assert exc.value.detail == "FACE_NOT_FOUND"

    async def test_decode_failed_400(self, patched: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
        """图片损坏 → 400 PHOTO_DECODE_FAILED。"""

        def raise_decode(data: bytes, bg_color: str) -> ProcessedPhoto:
            raise ImageDecodeError("broken")

        monkeypatch.setattr(api, "process_photo", raise_decode)
        with pytest.raises(HTTPException) as exc:
            await api.upload_photo(DRAFT_ID, _upload_file(b"x"), "white", _session())
        assert exc.value.status_code == 400
        assert exc.value.detail == "PHOTO_DECODE_FAILED"

    async def test_imaging_unavailable_501(self, patched: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
        """imaging 依赖未安装 → 501 IMAGING_NOT_AVAILABLE。"""

        def raise_missing(data: bytes, bg_color: str) -> ProcessedPhoto:
            raise ImagingNotAvailableError("no cv2")

        monkeypatch.setattr(api, "process_photo", raise_missing)
        with pytest.raises(HTTPException) as exc:
            await api.upload_photo(DRAFT_ID, _upload_file(b"x"), "white", _session())
        assert exc.value.status_code == 501
        assert exc.value.detail == "IMAGING_NOT_AVAILABLE"


class TestConfirmPhoto:
    """PUT /{draft_id}/photo/confirm。"""

    async def test_confirm_writes_identity_photo(self, patched: dict[str, Any]) -> None:
        """归属校验通过 → set_draft_photo 写入对象名。"""
        object_name = f"{DRAFT_ID}/processed-abcd1234.png"
        resp = await api.confirm_photo(
            DRAFT_ID,
            api.ConfirmPhotoRequest(object_name=object_name),
            _session(),
        )
        assert resp.code == 0
        assert patched["photo_set"] == [object_name]

    async def test_confirm_foreign_object_400(self, patched: dict[str, Any]) -> None:
        """对象名不属于该草稿 → 400 PHOTO_NOT_OWNED，不写入。"""
        other = "11111111-1111-1111-1111-111111111111/processed-x.png"
        with pytest.raises(HTTPException) as exc:
            await api.confirm_photo(DRAFT_ID, api.ConfirmPhotoRequest(object_name=other), _session())
        assert exc.value.status_code == 400
        assert exc.value.detail == "PHOTO_NOT_OWNED"
        assert patched["photo_set"] == []

    async def test_confirm_nonexistent_object_400(
        self, patched: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """前缀合法但 MinIO 中不存在的伪造对象名 → 400，不写入悬空引用。"""
        monkeypatch.setattr(api, "object_exists", lambda bucket, object_name: False)
        with pytest.raises(HTTPException) as exc:
            await api.confirm_photo(
                DRAFT_ID,
                api.ConfirmPhotoRequest(object_name=f"{DRAFT_ID}/processed-fabricated.png"),
                _session(),
            )
        assert exc.value.status_code == 400
        assert exc.value.detail == "PHOTO_NOT_OWNED"
        assert patched["photo_set"] == []

    async def test_confirm_original_object_rejected(self, patched: dict[str, Any]) -> None:
        """原图对象（非 processed-）不可 confirm。"""
        with pytest.raises(HTTPException) as exc:
            await api.confirm_photo(
                DRAFT_ID,
                api.ConfirmPhotoRequest(object_name=f"{DRAFT_ID}/original-abcd1234.jpg"),
                _session(),
            )
        assert exc.value.status_code == 400


class TestDeletePhoto:
    """DELETE /{draft_id}/photo。"""

    async def test_delete_clears_photo(self, patched: dict[str, Any]) -> None:
        """删除 → set_draft_photo(None) 清除字段。"""
        resp = await api.delete_photo(DRAFT_ID, _session())
        assert resp.code == 0
        assert patched["photo_set"] == [None]
