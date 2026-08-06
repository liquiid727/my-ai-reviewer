"""Unit tests for multimodal LLM capability contracts."""

from __future__ import annotations

import base64

import pytest

from backend.domain.llm.multimodal import (
    LLMCapabilities,
    MultimodalCapabilityError,
    MultimodalImageBlock,
    MultimodalMessage,
    MultimodalTextBlock,
    assert_can_dispatch_multimodal,
)
from backend.infrastructure.llm.providers.anthropic_provider import _convert_anthropic_content
from backend.infrastructure.llm.providers.openai_provider import _convert_openai_message


def _message() -> MultimodalMessage:
    image = MultimodalImageBlock(
        media_type="image/png",
        data_base64=base64.b64encode(b"synthetic-image").decode("ascii"),
        asset_id="asset-1",
    )
    return MultimodalMessage(role="user", content=[MultimodalTextBlock(text="Transcribe"), image])


def test_capability_check_rejects_unverified_or_text_only_vision() -> None:
    message = _message()
    with pytest.raises(MultimodalCapabilityError):
        assert_can_dispatch_multimodal(LLMCapabilities(supports_vision=False), [message])
    with pytest.raises(MultimodalCapabilityError):
        assert_can_dispatch_multimodal(LLMCapabilities(supports_vision=True, transport="openai_chat"), [message])


def test_capability_check_enforces_image_limits() -> None:
    message = _message()
    caps = LLMCapabilities(supports_vision=True, max_images=0, transport="openai_chat", verified_at="2026-08-05T00:00:00Z")
    with pytest.raises(MultimodalCapabilityError):
        assert_can_dispatch_multimodal(caps, [message])


def test_provider_payload_conversion_does_not_log_or_strip_base64() -> None:
    message = _message()
    openai_payload = _convert_openai_message(message)
    assert openai_payload["content"][1]["type"] == "image_url"
    assert openai_payload["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")

    anthropic_payload = _convert_anthropic_content(message)
    assert anthropic_payload[1]["type"] == "image"
    assert anthropic_payload[1]["source"]["media_type"] == "image/png"
