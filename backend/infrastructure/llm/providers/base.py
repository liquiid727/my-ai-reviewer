"""LLM 提供商基类 —— 定义统一的响应数据结构和提供商抽象接口。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    """LLM 调用响应：包含生成内容、模型名称和 token 用量。"""
    content: str                    # 生成的文本内容
    model: str                      # 实际使用的模型名称
    usage: dict = field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0})


class BaseLLMProvider(ABC):
    """LLM 提供商抽象基类：各提供商需实现 complete 方法。"""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        response_format: dict | None = None,
    ) -> LLMResponse:
        pass
