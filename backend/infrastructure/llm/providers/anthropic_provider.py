"""Anthropic 提供商 —— 适配 Anthropic Messages API 的差异。"""

from anthropic import AsyncAnthropic

from backend.infrastructure.llm.providers.base import BaseLLMProvider, LLMResponse


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude 系列模型的提供商实现。

    Anthropic API 的 system prompt 和消息格式与 OpenAI 不同，
    这里做了格式转换以保持网关层接口一致。
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._client = AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        messages: list[dict],
        response_format: dict | None = None,
    ) -> LLMResponse:
        """调用 Anthropic Messages API。"""
        system_text = ""
        converted: list[dict] = []

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
                "\n\nYou MUST respond with valid JSON only. "
                "No markdown, no explanation, just the JSON object."
            )
            system_text += json_instruction

        kwargs: dict = {
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
