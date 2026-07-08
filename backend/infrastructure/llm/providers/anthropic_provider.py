from anthropic import AsyncAnthropic

from backend.infrastructure.llm.providers.base import BaseLLMProvider, LLMResponse


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._client = AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        messages: list[dict],
        response_format: dict | None = None,
    ) -> LLMResponse:
        system_text = ""
        converted: list[dict] = []

        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                role = "assistant" if msg["role"] == "assistant" else "user"
                converted.append({"role": role, "content": msg["content"]})

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
