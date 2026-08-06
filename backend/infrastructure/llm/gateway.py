"""LLM 网关 —— 统一的大模型调用入口，屏蔽不同提供商的差异。"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from backend.config import get_settings
from backend.domain.llm.multimodal import (
    MultimodalCapabilityError,
    MultimodalMessage,
    assert_can_dispatch_multimodal,
    capabilities_from_dict,
)
from backend.domain.privacy import PrivacyGuard
from backend.infrastructure.llm.providers.anthropic_provider import AnthropicProvider
from backend.infrastructure.llm.providers.base import BaseLLMProvider, LLMResponse
from backend.infrastructure.llm.providers.openai_provider import OpenAIProvider
from backend.observability.events import emit_resume_event

if TYPE_CHECKING:
    from backend.infrastructure.db.models import LLMConfigModel


class LLMGateway:
    """LLM 统一网关：封装不同提供商的调用细节，对外提供一致的接口。"""

    def __init__(
        self,
        provider: BaseLLMProvider,
        *,
        request_timeout_seconds: float | None = None,
        capabilities: object | None = None,
    ) -> None:
        self._provider = provider
        self._capabilities = capabilities_from_dict(capabilities or {})
        self._request_timeout_seconds = (
            request_timeout_seconds
            if request_timeout_seconds is not None
            else get_settings().LLM_REQUEST_TIMEOUT_SECONDS
        )

    async def complete(
        self,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
        *,
        privacy_required: bool = False,
    ) -> LLMResponse:
        """发送对话消息并获取 LLM 响应。"""
        guard = PrivacyGuard()
        if privacy_required:
            guard.assert_masked(messages)
        started = time.monotonic()
        try:
            response = await asyncio.wait_for(
                self._provider.complete(messages, response_format=response_format),
                timeout=self._request_timeout_seconds,
            )
        except Exception as exc:
            # The exception body may contain a provider payload or prompt
            # fragment. Keep the event correlation-only and let the caller
            # map the exception to a safe public diagnostic.
            emit_resume_event(
                "resume.llm.failed",
                resource_id=None,
                error_code=(
                    "RESUME_LLM_REQUEST_TIMEOUT"
                    if "timeout" in type(exc).__name__.lower()
                    else "RESUME_PROCESSING_FAILED"
                ),
                retryable=True,
                level=logging.WARNING,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            raise
        if privacy_required:
            guard.assert_masked(response.content)
        emit_resume_event(
            "resume.llm.completed",
            resource_id=None,
            status="completed",
            duration_ms=int((time.monotonic() - started) * 1000),
            model=response.model,
        )
        return response

    async def complete_multimodal(
        self,
        messages: list[MultimodalMessage],
        response_format: dict[str, Any] | None = None,
        *,
        privacy_required: bool = False,
    ) -> LLMResponse:
        """Send provider-neutral multimodal messages after explicit capability checks."""
        assert_can_dispatch_multimodal(self._capabilities, messages)
        guard = PrivacyGuard()
        if privacy_required:
            guard.assert_masked([message.model_dump(mode="json") for message in messages])
        started = time.monotonic()
        try:
            response = await asyncio.wait_for(
                self._provider.complete_multimodal(messages, response_format=response_format),
                timeout=self._request_timeout_seconds,
            )
        except MultimodalCapabilityError:
            raise
        except Exception:
            emit_resume_event(
                "resume.llm.failed",
                resource_id=None,
                error_code="RESUME_PROCESSING_FAILED",
                retryable=True,
                level=logging.WARNING,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            raise
        if privacy_required:
            guard.assert_masked(response.content)
        emit_resume_event(
            "resume.llm.completed",
            resource_id=None,
            status="completed",
            duration_ms=int((time.monotonic() - started) * 1000),
            model=response.model,
        )
        return response

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
            timeout_seconds=get_settings().LLM_REQUEST_TIMEOUT_SECONDS,
        )
        capabilities = capabilities_from_dict(getattr(llm_config, "capabilities", None) or {}, provider=provider_name)
        return cls(
            provider=provider,
            request_timeout_seconds=get_settings().LLM_REQUEST_TIMEOUT_SECONDS,
            capabilities=capabilities,
        )

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
            timeout_seconds=settings.LLM_REQUEST_TIMEOUT_SECONDS,
        )
        return cls(
            provider=provider,
            request_timeout_seconds=settings.LLM_REQUEST_TIMEOUT_SECONDS,
            capabilities=capabilities_from_dict({}, provider=provider_name),
        )


def _build_provider(
    provider_name: str,
    api_key: str,
    model: str,
    base_url: str | None = None,
    timeout_seconds: float | None = None,
) -> BaseLLMProvider:
    """根据提供商名称构建对应的 LLM Provider 实例。"""
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model, timeout_seconds=timeout_seconds)

    # openai / deepseek / custom 都走 OpenAI 兼容接口
    return OpenAIProvider(
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )
