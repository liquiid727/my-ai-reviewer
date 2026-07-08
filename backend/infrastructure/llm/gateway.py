from __future__ import annotations

from typing import TYPE_CHECKING

from backend.infrastructure.llm.providers.base import BaseLLMProvider, LLMResponse
from backend.infrastructure.llm.providers.openai_provider import OpenAIProvider
from backend.infrastructure.llm.providers.anthropic_provider import AnthropicProvider

if TYPE_CHECKING:
    from backend.infrastructure.db.models import LLMConfigModel


class LLMGateway:
    def __init__(self, provider: BaseLLMProvider) -> None:
        self._provider = provider

    async def complete(
        self,
        messages: list[dict],
        response_format: dict | None = None,
    ) -> LLMResponse:
        return await self._provider.complete(messages, response_format=response_format)

    @classmethod
    def from_config(cls, llm_config: LLMConfigModel) -> LLMGateway:
        from backend.infrastructure.crypto.encryption import get_encryptor

        provider_name = llm_config.provider.lower()
        api_key = get_encryptor().decrypt(llm_config.api_key_encrypted)
        model = llm_config.model_name

        provider = _build_provider(
            provider_name=provider_name,
            api_key=api_key,
            model=model,
            base_url=llm_config.base_url,
        )
        return cls(provider=provider)

    @classmethod
    def from_settings(cls) -> LLMGateway:
        from backend.config import get_settings

        settings = get_settings()
        provider_name = settings.DEFAULT_LLM_PROVIDER.lower()
        model = settings.DEFAULT_LLM_MODEL

        if provider_name == "anthropic":
            api_key = settings.ANTHROPIC_API_KEY
            base_url = None
        else:
            api_key = settings.OPENAI_API_KEY
            base_url = settings.OPENAI_BASE_URL

        provider = _build_provider(
            provider_name=provider_name,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )
        return cls(provider=provider)


def _build_provider(
    provider_name: str,
    api_key: str,
    model: str,
    base_url: str | None = None,
) -> BaseLLMProvider:
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model)

    # openai, deepseek, custom all go through the OpenAI-compatible provider
    return OpenAIProvider(api_key=api_key, model=model, base_url=base_url)
