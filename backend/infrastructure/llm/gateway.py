"""LLM 网关 —— 统一的大模型调用入口，屏蔽不同提供商的差异。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.infrastructure.llm.providers.base import BaseLLMProvider, LLMResponse
from backend.infrastructure.llm.providers.openai_provider import OpenAIProvider
from backend.infrastructure.llm.providers.anthropic_provider import AnthropicProvider

if TYPE_CHECKING:
    from backend.infrastructure.db.models import LLMConfigModel


class LLMGateway:
    """LLM 统一网关：封装不同提供商的调用细节，对外提供一致的接口。"""

    def __init__(self, provider: BaseLLMProvider) -> None:
        self._provider = provider

    async def complete(
        self,
        messages: list[dict],
        response_format: dict | None = None,
    ) -> LLMResponse:
        """发送对话消息并获取 LLM 响应。"""
        return await self._provider.complete(messages, response_format=response_format)

    @classmethod
    def from_config(cls, llm_config: LLMConfigModel) -> LLMGateway:
        """从数据库配置创建网关实例（API Key 会自动解密）。"""
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
        """从全局环境变量配置创建网关实例。"""
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
    """根据提供商名称构建对应的 LLM Provider 实例。"""
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model)

    # openai / deepseek / custom 都走 OpenAI 兼容接口
    return OpenAIProvider(api_key=api_key, model=model, base_url=base_url)
