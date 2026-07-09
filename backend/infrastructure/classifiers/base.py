"""简历分类器基类 —— 定义分类结果数据结构和分类器抽象接口。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from backend.domain.resume.schemas import CandidateProfile


@dataclass
class ClassificationResult:
    """分类结果：包含技术方向、资历等级、行业标签和统计数据。"""
    tech_direction_tags: list[str] = field(default_factory=list)   # 技术方向标签（Backend/Frontend/AI 等）
    experience_level: str = "Unknown"                              # 资历等级（Junior/Mid/Senior/Staff）
    industry_tags: list[str] = field(default_factory=list)         # 行业标签（Fintech/E-commerce 等）
    stats: dict = field(default_factory=lambda: {
        "total_years": 0.0,        # 总工作年限
        "project_count": 0,        # 项目数量
        "tech_depth": 0,           # 技术深度（技能分类数 + 技能总数）
        "has_management": False,   # 是否有管理经验
    })


class ResumeClassifier(ABC):
    """简历分类器抽象基类。"""

    @property
    @abstractmethod
    def version(self) -> str: ...

    @abstractmethod
    def classify(self, profile: CandidateProfile) -> ClassificationResult: ...
