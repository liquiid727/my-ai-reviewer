"""Provider-neutral multimodal LLM contracts.

Domain code owns the message shape and capability policy. Provider adapters are
responsible for translating these blocks into SDK-specific payloads.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

LLMTransport = Literal["openai_chat", "anthropic_messages", "none"]


class LLMCapabilities(BaseModel):
    """Explicit LLM feature declaration persisted with an LLM config."""

    model_config = ConfigDict(extra="forbid")

    supports_text: bool = True
    supports_structured_output: bool = False
    supports_vision: bool = False
    max_images: int | None = None
    max_image_bytes: int | None = None
    transport: LLMTransport = "none"
    verified_at: datetime | None = None

    @classmethod
    def text_defaults(cls, *, transport: LLMTransport = "none") -> "LLMCapabilities":
        return cls(supports_text=True, supports_structured_output=False, supports_vision=False, transport=transport)


class MultimodalTextBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["text"] = "text"
    text: str = Field(min_length=1, max_length=100_000)


class MultimodalImageBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["image"] = "image"
    media_type: Literal["image/png", "image/jpeg", "image/webp"]
    data_base64: str = Field(min_length=1)
    asset_id: str | None = None

    @field_validator("data_base64")
    @classmethod
    def _valid_base64(cls, value: str) -> str:
        try:
            base64.b64decode(value, validate=True)
        except Exception as exc:
            raise ValueError("image block must contain valid base64") from exc
        return value

    @property
    def byte_size(self) -> int:
        return len(base64.b64decode(self.data_base64, validate=True))


MultimodalContentBlock = MultimodalTextBlock | MultimodalImageBlock


class MultimodalMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant"]
    content: list[MultimodalContentBlock]


class MultimodalCapabilityError(ValueError):
    """Safe capability failure raised before dispatching images to a provider."""


@dataclass(frozen=True)
class CapabilityCheckResult:
    image_count: int
    image_bytes: int


def infer_transport(provider: str) -> LLMTransport:
    normalized = provider.strip().lower()
    if normalized == "anthropic":
        return "anthropic_messages"
    if normalized in {"openai", "deepseek", "custom"}:
        return "openai_chat"
    return "none"


def capabilities_from_dict(value: object, *, provider: str = "") -> LLMCapabilities:
    if isinstance(value, LLMCapabilities):
        return value
    transport = infer_transport(provider)
    if not isinstance(value, dict) or not value:
        return LLMCapabilities.text_defaults(transport=transport)
    payload = dict(value)
    payload.setdefault("transport", transport)
    payload.setdefault("supports_text", True)
    return LLMCapabilities.model_validate(payload)


def assert_can_dispatch_multimodal(
    capabilities: LLMCapabilities,
    messages: list[MultimodalMessage],
    *,
    require_verified: bool = True,
) -> CapabilityCheckResult:
    images = [block for message in messages for block in message.content if isinstance(block, MultimodalImageBlock)]
    if not images:
        if not capabilities.supports_text:
            raise MultimodalCapabilityError("LLM configuration does not support text generation")
        return CapabilityCheckResult(image_count=0, image_bytes=0)
    if require_verified and capabilities.verified_at is None:
        raise MultimodalCapabilityError("Vision capability has not been verified")
    if not capabilities.supports_vision:
        raise MultimodalCapabilityError("LLM configuration does not support Vision")
    if capabilities.transport == "none":
        raise MultimodalCapabilityError("LLM provider does not expose a multimodal transport")
    if capabilities.max_images is not None and len(images) > capabilities.max_images:
        raise MultimodalCapabilityError("Too many images for this LLM configuration")
    total_bytes = 0
    for image in images:
        image_size = image.byte_size
        total_bytes += image_size
        if capabilities.max_image_bytes is not None and image_size > capabilities.max_image_bytes:
            raise MultimodalCapabilityError("Image is too large for this LLM configuration")
    return CapabilityCheckResult(image_count=len(images), image_bytes=total_bytes)


__all__ = [
    "CapabilityCheckResult",
    "LLMCapabilities",
    "LLMTransport",
    "MultimodalCapabilityError",
    "MultimodalContentBlock",
    "MultimodalImageBlock",
    "MultimodalMessage",
    "MultimodalTextBlock",
    "assert_can_dispatch_multimodal",
    "capabilities_from_dict",
    "infer_transport",
]
