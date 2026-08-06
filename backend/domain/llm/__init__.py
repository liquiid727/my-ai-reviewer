"""LLM domain contracts."""

from backend.domain.llm.multimodal import (
    CapabilityCheckResult,
    LLMCapabilities,
    LLMTransport,
    MultimodalCapabilityError,
    MultimodalContentBlock,
    MultimodalImageBlock,
    MultimodalMessage,
    MultimodalTextBlock,
    assert_can_dispatch_multimodal,
    capabilities_from_dict,
    infer_transport,
)

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
