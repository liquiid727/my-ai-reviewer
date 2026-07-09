"""LLM 模块 —— 导出网关和响应数据类。"""

from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.llm.providers.base import LLMResponse

__all__ = ["LLMGateway", "LLMResponse"]
