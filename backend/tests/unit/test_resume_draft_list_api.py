"""简历草稿列表删除与排序 API 契约测试。"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1 import resume_builder as api


class _FakeSession:
    pass


def _session() -> AsyncSession:
    return cast(AsyncSession, _FakeSession())


def _draft_model(draft_id: uuid.UUID, sort_order: int) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=draft_id,
        resume_id=None,
        title=f"Draft {draft_id}",
        template_id="classic",
        status="draft",
        sort_order=sort_order,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_delete_draft_returns_deleted_id(monkeypatch: pytest.MonkeyPatch) -> None:
    draft_id = uuid.uuid4()
    delete = AsyncMock()
    monkeypatch.setattr(api.services, "delete_draft", delete)

    response = await api.delete_draft(draft_id, _session())

    assert response.code == 0
    assert response.data == {"draft_id": str(draft_id)}
    delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_reorder_draft_returns_persisted_order(monkeypatch: pytest.MonkeyPatch) -> None:
    first_id, second_id = uuid.uuid4(), uuid.uuid4()
    persisted = [_draft_model(second_id, 0), _draft_model(first_id, 1)]
    reorder = AsyncMock(return_value=persisted)
    monkeypatch.setattr(api.services, "reorder_drafts", reorder)

    response = await api.reorder_drafts(
        api.DraftOrderRequest(draft_ids=[second_id, first_id]),
        _session(),
    )

    assert response.code == 0
    assert [item["draft_id"] for item in response.data] == [str(second_id), str(first_id)]
    assert [item["sort_order"] for item in response.data] == [0, 1]
    reorder.assert_awaited_once()


@pytest.mark.asyncio
async def test_reorder_draft_rejects_invalid_order(monkeypatch: pytest.MonkeyPatch) -> None:
    reorder = AsyncMock(side_effect=ValueError("Draft order contains duplicate ids"))
    monkeypatch.setattr(api.services, "reorder_drafts", reorder)
    duplicate_id = uuid.uuid4()

    response = await api.reorder_drafts(
        api.DraftOrderRequest(draft_ids=[duplicate_id, duplicate_id]),
        _session(),
    )

    assert response.code == 400
    assert response.data is None
