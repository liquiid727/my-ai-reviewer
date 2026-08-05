"""Builder GET preview 的 revision 级渲染缓存契约。"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1 import resume_builder as api
from backend.domain.resume_builder.enums import LayoutDensity, LayoutMode
from backend.domain.resume_builder.schemas import ExportResult, LayoutPolicy
from backend.infrastructure.rendering.pdf_renderer import should_stop_rendering


class _Session:
    pass


def _as_session() -> AsyncSession:
    return cast(AsyncSession, _Session())


def _model(revision: int = 3) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), revision=revision)


def _patch_cache(
    monkeypatch: pytest.MonkeyPatch,
    *,
    pdf: bytes | None,
    meta: dict[str, Any] | None,
) -> dict[str, list[tuple[str, bytes]]]:
    """把 api 模块内直接引用的缓存函数替换为内存实现，并记录写入。"""
    writes: dict[str, list[tuple[str, bytes]]] = {"set": []}

    async def fake_get_bytes(key: str) -> bytes | None:
        return pdf

    async def fake_get_json(key: str) -> dict[str, Any] | None:
        return meta

    async def fake_set_bytes(key: str, value: bytes, ttl_seconds: int) -> None:
        writes["set"].append((key, value))

    async def fake_set_json(key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        writes["set"].append((key, b"json"))

    monkeypatch.setattr(api, "cache_get_bytes", fake_get_bytes)
    monkeypatch.setattr(api, "cache_get_json", fake_get_json)
    monkeypatch.setattr(api, "cache_set_bytes", fake_set_bytes)
    monkeypatch.setattr(api, "cache_set_json", fake_set_json)
    return writes


@pytest.mark.asyncio
async def test_preview_cache_hit_skips_rendering(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _model()
    rendered: list[int] = []

    async def fake_get_draft(session: Any, value: uuid.UUID) -> Any:
        return model

    async def fake_export(*args: Any, **kwargs: Any) -> tuple[bytes, ExportResult]:
        rendered.append(1)
        raise AssertionError("export_draft_pdf must not be called on cache hit")

    cached_meta = {"page_count": 2, "target_met": True, "applied_density": "normal"}
    _patch_cache(monkeypatch, pdf=b"cached-pdf", meta=cached_meta)
    monkeypatch.setattr(api.services, "get_draft", fake_get_draft)
    monkeypatch.setattr(api.services, "export_draft_pdf", fake_export)

    response = await api.preview_draft(model.id, _as_session())

    assert response.body == b"cached-pdf"
    assert response.headers["X-Page-Count"] == "2"
    assert response.headers["X-Layout-Density"] == "normal"
    assert response.headers["Cache-Control"] == "no-store"
    assert rendered == []


@pytest.mark.asyncio
async def test_preview_cache_miss_renders_and_stores_by_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _model(revision=7)
    result = ExportResult(
        page_count=1,
        target_met=True,
        applied_density=LayoutDensity.LOOSE,
    )

    async def fake_get_draft(session: Any, value: uuid.UUID) -> Any:
        return model

    async def fake_export(session: Any, draft: Any, options: Any) -> tuple[bytes, ExportResult]:
        return b"fresh-pdf", result

    writes = _patch_cache(monkeypatch, pdf=None, meta=None)
    monkeypatch.setattr(api.services, "get_draft", fake_get_draft)
    monkeypatch.setattr(api.services, "export_draft_pdf", fake_export)

    response = await api.preview_draft(model.id, _as_session())

    assert response.body == b"fresh-pdf"
    assert response.headers["X-Page-Count"] == "1"
    assert response.headers["X-Target-Met"] == "true"
    # 缓存键必须携带 revision，保证内容变更后不会命中旧 PDF
    keys = [key for key, _ in writes["set"]]
    assert f"builder:preview:{model.id}:r7:pdf" in keys
    assert f"builder:preview:{model.id}:r7:meta" in keys


@pytest.mark.asyncio
async def test_preview_cache_hit_requires_both_pdf_and_meta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """只有 PDF 没有元信息（或反之）时视为未命中，回退到渲染路径。"""
    model = _model()
    rendered: list[int] = []
    result = ExportResult(page_count=1, target_met=True, applied_density=LayoutDensity.NORMAL)

    async def fake_get_draft(session: Any, value: uuid.UUID) -> Any:
        return model

    async def fake_export(session: Any, draft: Any, options: Any) -> tuple[bytes, ExportResult]:
        rendered.append(1)
        return b"fresh-pdf", result

    _patch_cache(monkeypatch, pdf=b"cached-pdf", meta=None)
    monkeypatch.setattr(api.services, "get_draft", fake_get_draft)
    monkeypatch.setattr(api.services, "export_draft_pdf", fake_export)

    response = await api.preview_draft(model.id, _as_session())

    assert response.body == b"fresh-pdf"
    assert rendered == [1]


def test_should_stop_rendering_exact_target_match() -> None:
    policy = LayoutPolicy(mode=LayoutMode.TARGET_PAGES, target_page_count=2)

    assert should_stop_rendering(policy, 2) is True
    assert should_stop_rendering(policy, 3) is False


def test_should_stop_rendering_auto_mode_stops_at_single_page() -> None:
    policy = LayoutPolicy()

    assert should_stop_rendering(policy, 1) is True
    assert should_stop_rendering(policy, 2) is False
