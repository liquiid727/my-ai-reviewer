from abc import ABC, abstractmethod


class ResumeEvaluator(ABC):
    @abstractmethod
    async def evaluate(self, parsed_result: dict) -> dict:
        pass
