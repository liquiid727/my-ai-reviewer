from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict = field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0})


class BaseLLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        response_format: dict | None = None,
    ) -> LLMResponse:
        pass
