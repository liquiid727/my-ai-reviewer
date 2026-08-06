from typing import cast
from unittest.mock import AsyncMock

import pytest

from backend.application import interview_service
from backend.infrastructure.llm.gateway import LLMGateway


@pytest.mark.asyncio
async def test_interview_gateway_uses_active_verified_database_config(monkeypatch: pytest.MonkeyPatch) -> None:
    config = object()
    gateway = cast(LLMGateway, object())
    session = type("Session", (), {"rollback": AsyncMock()})()

    async def get_config(_session: object) -> object:
        return config

    monkeypatch.setattr("backend.application.llm_config_service.get_active_verified_config", get_config)
    monkeypatch.setattr(interview_service.LLMGateway, "from_config", classmethod(lambda _cls, value: gateway))

    result = await interview_service.get_interview_llm_gateway(session)  # type: ignore[arg-type]

    assert result is gateway
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_interview_gateway_rejects_missing_verified_config(monkeypatch: pytest.MonkeyPatch) -> None:
    session = type("Session", (), {"rollback": AsyncMock()})()

    async def get_config(_session: object) -> None:
        return None

    monkeypatch.setattr("backend.application.llm_config_service.get_active_verified_config", get_config)

    with pytest.raises(ValueError, match="LLM_NOT_READY"):
        await interview_service.get_interview_llm_gateway(session)  # type: ignore[arg-type]

    session.rollback.assert_awaited_once()
