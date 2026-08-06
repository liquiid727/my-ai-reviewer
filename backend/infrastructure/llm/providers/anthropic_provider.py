"""Anthropic 提供商 —— 适配 Anthropic Messages API 的差异。"""

from typing import Any

from anthropic import AsyncAnthropic

from backend.domain.llm.multimodal import MultimodalImageBlock, MultimodalMessage, MultimodalTextBlock
from backend.infrastructure.llm.providers.base import BaseLLMProvider, LLMResponse


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude 系列模型的提供商实现。

    Anthropic API 的 system prompt 和消息格式与 OpenAI 不同，
    这里做了格式转换以保持网关层接口一致。
    """

    def __init__(self, api_key: str, model: str, timeout_seconds: float | None = None) -> None:
        self._model = model
        self._client = AsyncAnthropic(api_key=api_key, timeout=timeout_seconds)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """调用 Anthropic Messages API。"""
        system_text = ""
        converted: list[dict[str, Any]] = []

        # 将统一的 messages 格式转换为 Anthropic 的格式
        # Anthropic 的 system prompt 需要单独传入，不放在 messages 中
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                role = "assistant" if msg["role"] == "assistant" else "user"
                converted.append({"role": role, "content": msg["content"]})

        # Anthropic 不直接支持 response_format，通过在 system prompt 中追加指令来约束输出格式
        if response_format is not None:
            json_instruction = (
                "\n\nYou MUST respond with valid JSON only. No markdown, no explanation, just the JSON object."
            )
            system_text += json_instruction

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": converted,
            "max_tokens": 8192,
        }
        if system_text:
            kwargs["system"] = system_text

        response = await self._client.messages.create(**kwargs)

        # 拼接所有文本块的内容
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return LLMResponse(
            content=content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
        )

    async def complete_multimodal(
        self,
        messages: list[MultimodalMessage],
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        system_text = ""
        converted: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "system":
                system_text = "\n".join(
                    block.text for block in message.content if isinstance(block, MultimodalTextBlock)
                )
                continue
            converted.append({"role": message.role, "content": _convert_anthropic_content(message)})
        if response_format is not None:
            system_text += "\n\nRespond with valid JSON only."
        kwargs: dict[str, Any] = {"model": self._model, "messages": converted, "max_tokens": 8192}
        if system_text:
            kwargs["system"] = system_text
        response = await self._client.messages.create(**kwargs)
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text
        return LLMResponse(
            content=content,
            model=response.model,
            usage={"prompt_tokens": response.usage.input_tokens, "completion_tokens": response.usage.output_tokens},
        )


def _convert_anthropic_content(message: MultimodalMessage) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for block in message.content:
        if isinstance(block, MultimodalTextBlock):
            converted.append({"type": "text", "text": block.text})
        elif isinstance(block, MultimodalImageBlock):
            converted.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": block.media_type, "data": block.data_base64},
                }
            )
    return converted
