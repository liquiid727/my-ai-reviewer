"""Central LLM privacy boundary."""

from __future__ import annotations

from typing import Any

import pytest

from backend.domain.privacy import PrivacyViolationError
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.providers.base import LLMResponse


class _Provider:
    def __init__(self) -> None:
        self.calls = 0

    async def complete(
        self,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        self.calls += 1
        return LLMResponse(content="{}", model="test", usage={})


@pytest.mark.asyncio
async def test_privacy_classified_llm_request_blocks_cleartext_before_provider() -> None:
    provider = _Provider()
    gateway = LLMGateway(provider)  # type: ignore[arg-type]

    with pytest.raises(PrivacyViolationError):
        await gateway.complete(
            [{"role": "user", "content": "phone 13800138000"}],
            privacy_required=True,
        )

    assert provider.calls == 0


@pytest.mark.asyncio
async def test_privacy_classified_llm_request_allows_masked_payload() -> None:
    provider = _Provider()
    gateway = LLMGateway(provider)  # type: ignore[arg-type]

    await gateway.complete(
        [{"role": "user", "content": "phone [[PHONE_01]]"}],
        privacy_required=True,
    )

    assert provider.calls == 1
