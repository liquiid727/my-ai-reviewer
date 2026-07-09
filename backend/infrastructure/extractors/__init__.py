"""简历信息提取器模块 —— 导出提取器基类和 LLM 提取器实现。"""

from backend.infrastructure.extractors.base import ResumeExtractor
from backend.infrastructure.extractors.llm_extractor import LLMResumeExtractor

__all__ = ["ResumeExtractor", "LLMResumeExtractor"]
