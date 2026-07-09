"""简历分类器模块 —— 导出分类器基类和规则分类器实现。"""

from backend.infrastructure.classifiers.base import ResumeClassifier, ClassificationResult
from backend.infrastructure.classifiers.rule_classifier import RuleBasedResumeClassifier

__all__ = ["ResumeClassifier", "ClassificationResult", "RuleBasedResumeClassifier"]
