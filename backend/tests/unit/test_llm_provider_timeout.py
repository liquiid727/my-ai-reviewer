"""LLM providers must receive the configured request timeout."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.providers import anthropic_provider, openai_provider


def test_openai_provider_passes_request_timeout(monkeypatch: Any) -> None:
    seen: dict[str, Any] = {}

    class _Client:
        def __init__(self, **kwargs: Any) -> None:
            seen.update(kwargs)

    monkeypatch.setattr(openai_provider, "AsyncOpenAI", _Client)

    openai_provider.OpenAIProvider(
        api_key="synthetic-key",
        model="synthetic-model",
        timeout_seconds=90.0,
    )

    assert seen["timeout"] == 90.0


@pytest.mark.asyncio
async def test_gateway_enforces_outer_request_timeout() -> None:
    class _Provider:
        async def complete(self, _messages: list[dict[str, Any]], **_kwargs: Any) -> Any:
            await asyncio.sleep(1)

    with pytest.raises(asyncio.TimeoutError):
        await LLMGateway(_Provider(), request_timeout_seconds=0.001).complete([])  # type: ignore[arg-type]


def test_anthropic_provider_passes_request_timeout(monkeypatch: Any) -> None:
    seen: dict[str, Any] = {}

    class _Client:
        def __init__(self, **kwargs: Any) -> None:
            seen.update(kwargs)

    monkeypatch.setattr(anthropic_provider, "AsyncAnthropic", _Client)

    anthropic_provider.AnthropicProvider(
        api_key="synthetic-key",
        model="synthetic-model",
        timeout_seconds=90.0,
    )

    assert seen["timeout"] == 90.0
