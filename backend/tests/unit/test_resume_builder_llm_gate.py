"""简历制作器 AI 入口的 LLM 配置门禁契约测试。"""

import uuid
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from backend.api.v1 import resume_builder as api
from backend.domain.resume.enums import ResumeSectionType


class _FakeSession:
    pass


@pytest.mark.asyncio
async def test_polish_returns_llm_not_ready_without_verified_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_config = _async_return(None)
    monkeypatch.setattr(api.llm_config_service, "get_active_verified_config", get_config)
    monkeypatch.setattr(api.services, "get_draft", _async_return(object()))

    response = await api.polish_section(
        uuid.uuid4(),
        api.PolishSectionRequest(
            section_type=ResumeSectionType.WORK_EXPERIENCE,
            items=["负责服务开发"],
        ),
        _FakeSession(),  # type: ignore[arg-type]
    )

    assert response.code == api.LLM_NOT_READY_CODE
    assert response.data is None
    get_config.assert_awaited_once()


@pytest.mark.asyncio
async def test_score_returns_llm_not_ready_without_verified_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_config = _async_return(None)
    monkeypatch.setattr(api.llm_config_service, "get_active_verified_config", get_config)
    monkeypatch.setattr(api.services, "get_draft", _async_return(object()))

    response = await api.score_draft(uuid.uuid4(), _FakeSession())  # type: ignore[arg-type]

    assert response.code == api.LLM_NOT_READY_CODE
    assert response.data is None
    get_config.assert_awaited_once()


@pytest.mark.asyncio
async def test_score_uses_active_verified_config_for_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = object()
    gateway = object()
    draft_model = object()
    draft_schema = object()
    get_config = _async_return(config)
    get_draft = _async_return(draft_model)
    score = AsyncMock(return_value={"overall_score": 92})
    from_config = Mock(return_value=gateway)

    monkeypatch.setattr(api.llm_config_service, "get_active_verified_config", get_config)
    monkeypatch.setattr(api.services, "get_draft", get_draft)
    monkeypatch.setattr(api.services, "draft_model_to_schema", Mock(return_value=draft_schema))
    monkeypatch.setattr(api.services, "score_draft", score)
    monkeypatch.setattr(api.LLMGateway, "from_config", from_config)

    response = await api.score_draft(uuid.uuid4(), _FakeSession())  # type: ignore[arg-type]

    assert response.code == 0
    assert response.data == {"overall_score": 92}
    from_config.assert_called_once_with(config)
    score.assert_awaited_once_with(gateway, draft_schema)


def _async_return(value: Any):
    return AsyncMock(return_value=value)
