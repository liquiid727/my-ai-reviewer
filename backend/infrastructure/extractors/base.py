from abc import ABC, abstractmethod


class ResumeExtractor(ABC):
    version: str = "base"

    @abstractmethod
    async def extract(self, raw_text: str) -> dict:
        pass
