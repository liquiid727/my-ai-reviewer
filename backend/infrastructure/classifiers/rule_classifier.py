"""基于规则的简历分类器 —— 通过关键词匹配和工作年限计算对候选人进行分类。"""

import re
from datetime import date

from backend.domain.resume.schemas import CandidateProfile, WorkExperience
from backend.infrastructure.classifiers.base import ClassificationResult, ResumeClassifier

# 技术方向关键词映射：方向名 → 相关技术关键词集合
TECH_DIRECTION_KEYWORDS: dict[str, set[str]] = {
    "Backend": {
        "python", "java", "go", "fastapi", "spring", "django", "flask",
        "redis", "kafka", "postgresql", "mysql",
    },
    "Frontend": {
        "react", "vue", "angular", "typescript", "javascript", "css", "html",
    },
    "AI": {
        "pytorch", "tensorflow", "llm", "ml", "nlp", "cv",
        "deep-learning", "langchain",
    },
    "DevOps": {
        "docker", "kubernetes", "ci-cd", "terraform", "ansible",
        "aws", "gcp", "azure",
    },
    "Data": {
        "spark", "hadoop", "flink", "etl", "data-pipeline",
        "sql", "pandas", "airflow",
    },
}

# 管理经验相关关键词
MANAGEMENT_KEYWORDS: set[str] = {
    "manager", "lead", "director", "head", "vp", "chief",
    "team lead", "tech lead", "engineering manager",
    "management", "leading", "managed", "supervised",
}

# 日期解析正则：匹配 "2023-01"、"2023/1"、"2023.01" 等格式
_DATE_PATTERN = re.compile(r"(\d{4})[-/.](\d{1,2})")


def _parse_date(raw: str | None) -> date | None:
    """解析日期字符串，支持 年-月 和 纯年份 格式。"""
    if not raw:
        return None
    m = _DATE_PATTERN.search(raw)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        month = max(1, min(month, 12))
        return date(year, month, 1)
    # 退而求其次：只有年份
    year_only = re.search(r"\d{4}", raw)
    if year_only:
        return date(int(year_only.group()), 1, 1)
    return None


def _compute_total_years(experiences: list[WorkExperience]) -> float:
    """计算所有工作经历的总年限。"""
    total_months = 0
    for exp in experiences:
        start = _parse_date(exp.start_date)
        if start is None:
            continue
        end = _parse_date(exp.end_date) or date.today()
        months = (end.year - start.year) * 12 + (end.month - start.month)
        total_months += max(months, 0)
    return round(total_months / 12, 1)


def _experience_level(total_years: float) -> str:
    """根据总工作年限判定资历等级。"""
    if total_years <= 2:
        return "Junior"      # 初级：0~2 年
    if total_years <= 5:
        return "Mid"         # 中级：3~5 年
    if total_years <= 9:
        return "Senior"      # 高级：6~9 年
    return "Staff"           # 资深：10 年以上


def _has_management(experiences: list[WorkExperience]) -> bool:
    """判断是否有管理经验（在职位、职责或成就中出现管理关键词）。"""
    for exp in experiences:
        searchable = " ".join([
            exp.title or "",
            *exp.responsibilities,
            *exp.achievements,
        ]).lower()
        for kw in MANAGEMENT_KEYWORDS:
            if kw in searchable:
                return True
    return False


def _extract_industry_tags(experiences: list[WorkExperience]) -> list[str]:
    """根据工作经历中的关键词推断候选人的行业背景。"""
    industry_hints: dict[str, list[str]] = {
        "Fintech": ["bank", "fintech", "payment", "financial", "insurance"],
        "E-commerce": ["ecommerce", "e-commerce", "retail", "shop", "marketplace"],
        "Healthcare": ["health", "medical", "hospital", "pharma", "biotech"],
        "Education": ["education", "edtech", "university", "school", "learning"],
        "Gaming": ["game", "gaming", "esports"],
        "Social": ["social", "community", "chat", "messaging"],
        "Enterprise": ["enterprise", "saas", "b2b", "crm", "erp"],
        "Media": ["media", "news", "content", "streaming", "video"],
        "Telecom": ["telecom", "telco", "mobile operator"],
        "Logistics": ["logistics", "supply chain", "shipping", "warehouse"],
    }

    found: set[str] = set()
    for exp in experiences:
        searchable = " ".join([
            exp.company or "",
            exp.title or "",
            *exp.responsibilities,
        ]).lower()
        for tag, keywords in industry_hints.items():
            if any(kw in searchable for kw in keywords):
                found.add(tag)
    return sorted(found)


class RuleBasedResumeClassifier(ResumeClassifier):
    """基于规则的简历分类器实现。

    通过技能关键词匹配技术方向，根据工作年限判定资历等级，
    从工作经历中推断行业背景。
    """

    @property
    def version(self) -> str:
        return "rule-classifier-v1"

    def classify(self, profile: CandidateProfile) -> ClassificationResult:
        # 收集所有技能名（小写）
        skill_names = {s.name.lower().strip() for s in profile.skills}

        # 匹配技术方向：技能集合与方向关键词取交集
        tech_direction_tags: list[str] = []
        for direction, keywords in TECH_DIRECTION_KEYWORDS.items():
            if skill_names & keywords:
                tech_direction_tags.append(direction)

        # 计算总工作年限
        total_years = _compute_total_years(profile.work_experiences)

        # 技术深度 = 技能分类数 + 技能总数
        unique_categories = {
            s.category for s in profile.skills if s.category
        }
        tech_depth = len(unique_categories) + len(profile.skills)

        return ClassificationResult(
            tech_direction_tags=sorted(tech_direction_tags),
            experience_level=_experience_level(total_years),
            industry_tags=_extract_industry_tags(profile.work_experiences),
            stats={
                "total_years": total_years,
                "project_count": len(profile.projects),
                "tech_depth": tech_depth,
                "has_management": _has_management(profile.work_experiences),
            },
        )
