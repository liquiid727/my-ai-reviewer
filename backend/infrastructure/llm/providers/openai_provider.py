"""OpenAI 兼容提供商 —— 支持 OpenAI、DeepSeek 等 OpenAI 接口兼容的模型服务。"""

from typing import Any

from openai import AsyncOpenAI

from backend.domain.llm.multimodal import MultimodalImageBlock, MultimodalMessage, MultimodalTextBlock
from backend.infrastructure.llm.providers.base import BaseLLMProvider, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """OpenAI 兼容的 LLM 提供商实现。

    通过 base_url 参数支持 DeepSeek、自部署等 OpenAI API 兼容服务。
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._model = model
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )

    async def complete(
        self,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """调用 OpenAI Chat Completions API。"""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        response = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
            },
        )

    async def complete_multimodal(
        self,
        messages: list[MultimodalMessage],
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        converted = [_convert_openai_message(message) for message in messages]
        return await self.complete(converted, response_format=response_format)


def _convert_openai_message(message: MultimodalMessage) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    for block in message.content:
        if isinstance(block, MultimodalTextBlock):
            content.append({"type": "text", "text": block.text})
        elif isinstance(block, MultimodalImageBlock):
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{block.media_type};base64,{block.data_base64}"},
                }
            )
    if message.role == "system":
        text = "\n".join(block.text for block in message.content if isinstance(block, MultimodalTextBlock))
        return {"role": "system", "content": text}
    return {"role": message.role, "content": content}
