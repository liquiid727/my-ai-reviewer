from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ParsedResumeText:
    raw_text: str
    page_count: int | None = None


class ResumeParser(ABC):
    @property
    @abstractmethod
    def version(self) -> str: ...

    @abstractmethod
    def parse(self, file_path: str) -> ParsedResumeText: ...
