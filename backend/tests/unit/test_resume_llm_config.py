"""Resume LLM stages must use the active verified database configuration."""

from __future__ import annotations

import uuid
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.resume_service import pipeline as services
from backend.domain.resume.enums import ResumeStatus


class _FakeResume:
    def __init__(self, parsed_result: dict[str, Any]) -> None:
        self.masked_text = "Experienced engineer [[NAME_01]]"
        self.parsed_result = parsed_result
        self.status = ResumeStatus.TEXT_MASKED


class _FakeManifest:
    status = "approved"


class _FakeSession:
    def __init__(self, resume: _FakeResume) -> None:
        self.resume = resume
        self.added: list[Any] = []
        self.commits = 0

    async def get(self, model: Any, _resume_id: uuid.UUID) -> Any:
        return self.resume

    async def scalar(self, _statement: Any) -> _FakeManifest:
        return _FakeManifest()

    def add(self, value: Any) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        self.commits += 1


@pytest.mark.asyncio
async def test_extract_facts_uses_active_verified_database_llm_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = object()
    gateway = object()
    session = _FakeSession(_FakeResume({"text_blocks": []}))
    get_config = AsyncMock(return_value=config)
    from_config = Mock(return_value=gateway)
    seen_gateways: list[object] = []

    class _Extractor:
        version = "test-extractor"

        def __init__(self, actual_gateway: object) -> None:
            seen_gateways.append(actual_gateway)

        async def extract(self, _masked_text: str) -> dict[str, Any]:
            return {"facts": [], "profile": {}}

    monkeypatch.setattr(services, "get_active_verified_config", get_config, raising=False)
    monkeypatch.setattr(services.LLMGateway, "from_config", from_config)
    monkeypatch.setattr(services.LLMGateway, "from_settings", Mock(side_effect=AssertionError("env config used")))
    monkeypatch.setattr(services, "LLMResumeExtractor", _Extractor)

    result = await services.extract_facts(cast(AsyncSession, session), uuid.uuid4())

    assert result.status == ResumeStatus.FACT_EXTRACTED
    get_config.assert_awaited_once_with(session)
    from_config.assert_called_once_with(config)
    assert seen_gateways == [gateway]


@pytest.mark.asyncio
async def test_evaluate_resume_uses_active_verified_database_llm_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = object()
    gateway = object()
    session = _FakeSession(_FakeResume({"profile": {"skills": ["Python"]}}))
    get_config = AsyncMock(return_value=config)
    from_config = Mock(return_value=gateway)
    seen_gateways: list[object] = []

    class _Evaluator:
        def __init__(self, actual_gateway: object) -> None:
            seen_gateways.append(actual_gateway)

        async def evaluate(self, _parsed_result: dict[str, Any]) -> dict[str, Any]:
            return {
                "overall_score": 88,
                "dimension_scores": [],
                "_meta": {"model": "db-config-model"},
            }

    monkeypatch.setattr(services, "get_active_verified_config", get_config, raising=False)
    monkeypatch.setattr(services.LLMGateway, "from_config", from_config)
    monkeypatch.setattr(services.LLMGateway, "from_settings", Mock(side_effect=AssertionError("env config used")))
    monkeypatch.setattr(services, "LLMResumeEvaluator", _Evaluator)

    result = await services.evaluate_resume(cast(AsyncSession, session), uuid.uuid4())

    assert result.status == ResumeStatus.EVALUATED
    get_config.assert_awaited_once_with(session)
    from_config.assert_called_once_with(config)
    assert seen_gateways == [gateway]
    assert session.commits == 1
