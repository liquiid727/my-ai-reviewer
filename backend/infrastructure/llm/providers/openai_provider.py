"""OpenAI 兼容提供商 —— 支持 OpenAI、DeepSeek 等 OpenAI 接口兼容的模型服务。"""

from openai import AsyncOpenAI

from backend.infrastructure.llm.providers.base import BaseLLMProvider, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """OpenAI 兼容的 LLM 提供商实现。

    通过 base_url 参数支持 DeepSeek、自部署等 OpenAI API 兼容服务。
    """

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        self._model = model
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    async def complete(
        self,
        messages: list[dict],
        response_format: dict | None = None,
    ) -> LLMResponse:
        """调用 OpenAI Chat Completions API。"""
        kwargs: dict = {
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
