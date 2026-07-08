from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from backend.domain.resume.schemas import CandidateProfile


@dataclass
class ClassificationResult:
    tech_direction_tags: list[str] = field(default_factory=list)
    experience_level: str = "Unknown"
    industry_tags: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=lambda: {
        "total_years": 0.0,
        "project_count": 0,
        "tech_depth": 0,
        "has_management": False,
    })


class ResumeClassifier(ABC):

    @property
    @abstractmethod
    def version(self) -> str: ...

    @abstractmethod
    def classify(self, profile: CandidateProfile) -> ClassificationResult: ...
