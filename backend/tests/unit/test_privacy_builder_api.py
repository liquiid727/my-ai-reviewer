"""Transient Builder preview/export API contracts."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1 import resume_builder as api
from backend.domain.resume_builder.enums import LayoutDensity
from backend.domain.resume_builder.schemas import ExportResult


class _Session:
    pass


def _as_session() -> AsyncSession:
    return cast(AsyncSession, _Session())


@pytest.mark.asyncio
async def test_export_uses_transient_replacements_and_sets_no_store(monkeypatch: pytest.MonkeyPatch) -> None:
    draft_id = uuid.uuid4()
    model = SimpleNamespace(id=draft_id, title="[[PERSON_01]]")
    captured: dict[str, Any] = {}

    async def fake_get_draft(session: Any, value: uuid.UUID) -> Any:
        return model

    async def fake_export(session: Any, draft: Any, options: Any) -> tuple[bytes, ExportResult]:
        captured["replacements"] = options.replacements
        captured["persist"] = options.persist
        return b"pdf", ExportResult(page_count=1, applied_density=LayoutDensity.NORMAL)

    monkeypatch.setattr(api.services, "get_draft", fake_get_draft)
    monkeypatch.setattr(api.services, "export_draft_pdf", fake_export)

    response = await api.export_draft(
        draft_id,
        api.ExportRequest(replacements={"[[PERSON_01]]": "张三"}, persist=True),
        _as_session(),
    )

    assert response.headers["Cache-Control"] == "no-store"
    assert captured == {"replacements": {"[[PERSON_01]]": "张三"}, "persist": False}


def test_serialized_draft_returns_safe_placeholder_manifest_only() -> None:
    model = SimpleNamespace(
        id=uuid.uuid4(),
        resume_id=None,
        title="[[PERSON_01]]",
        template_id="classic",
        layout_mode="auto_pages",
        target_page_count=None,
        status="draft",
        revision=1,
        content={"identity": {"name": "[[PERSON_01]]"}, "summary": None, "sections": []},
        design_tokens={},
        privacy_manifest={"placeholders": [{"token": "[[PERSON_01]]", "entity_type": "person"}]},
    )

    payload = api._serialize_draft(model)

    assert payload["privacy_placeholders"] == [{"token": "[[PERSON_01]]", "entity_type": "person"}]
