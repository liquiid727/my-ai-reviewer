"""基于规则的简历分类器 —— 通过关键词匹配和工作年限计算对候选人进行分类。"""

import re
from datetime import date

from backend.domain.resume.schemas import CandidateProfile, WorkExperience
from backend.infrastructure.classifiers.base import ClassificationResult, ResumeClassifier

# 技术方向关键词映射：方向名 → 相关技术关键词集合
TECH_DIRECTION_KEYWORDS: dict[str, set[str]] = {
    "Backend": {
        "python", "java", "go", "fastapi", "spring", "django", "flask",
        "redis", "kafka", "postgresql", "mysql", "grpc", "microservice",
    },
    "Frontend": {
        "react", "vue", "angular", "typescript", "javascript", "css", "html",
        "webpack", "vite", "next.js", "tailwind",
    },
    "AI": {
        "pytorch", "tensorflow", "ml", "nlp", "cv",
        "deep-learning", "machine learning", "scikit-learn", "keras",
    },
    "LLM Engineer": {
        "llm", "langchain", "langgraph", "rag", "prompt", "openai",
        "vector database", "embedding", "fine-tuning", "agent",
    },
    "Architect": {
        "architecture", "architect", "system design", "ddd",
        "high availability", "scalability",
    },
    "DevOps": {
        "docker", "kubernetes", "ci-cd", "terraform", "ansible",
        "prometheus", "grafana", "jenkins", "gitlab-ci",
    },
    "Cloud Native": {
        "kubernetes", "istio", "helm", "serverless", "service mesh",
        "cloud-native", "cloud native", "aws", "gcp", "azure",
    },
    "Distributed System": {
        "distributed", "distributed system", "consensus", "raft", "paxos",
        "sharding", "consistent hashing", "zookeeper", "etcd",
    },
    "Data": {
        "spark", "hadoop", "flink", "etl", "data-pipeline",
        "sql", "pandas", "airflow", "data warehouse",
    },
    "Game": {
        "unity", "unreal", "cocos", "game engine", "game development",
    },
    "Mobile": {
        "android", "ios", "flutter", "react native", "swift", "kotlin",
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


def _build_search_corpus(profile: CandidateProfile) -> tuple[set[str], str]:
    """从技能 + 项目技术栈 + 工作职责/职位 构建匹配语料。

    返回：(token 集合（用于短关键词精确匹配）, 拼接后的小写长文本（用于多词短语子串匹配）)。
    分开两种匹配方式：短词（如 go/ml/cv）用 token 精确匹配避免误判（go ≠ good），
    含空格的多词短语（如 system design）用子串匹配。
    """
    parts: list[str] = []
    for s in profile.skills:
        parts.append(s.name)
    for p in profile.projects:
        parts.extend(p.tech_stack)
    for exp in profile.work_experiences:
        parts.append(exp.title or "")
        parts.extend(exp.responsibilities)
        parts.extend(exp.tech_stack)

    joined = " ".join(parts).lower()
    tokens = {tok for tok in re.split(r"[^a-z0-9+.#-]+", joined) if tok}
    return tokens, joined


def _match_directions(tokens: set[str], corpus: str) -> list[str]:
    """根据语料匹配技术方向标签。"""
    matched: list[str] = []
    for direction, keywords in TECH_DIRECTION_KEYWORDS.items():
        for kw in keywords:
            kw_l = kw.lower()
            if " " in kw_l:
                # 多词短语：子串匹配
                if kw_l in corpus:
                    matched.append(direction)
                    break
            elif kw_l in tokens:
                # 单词：精确 token 匹配
                matched.append(direction)
                break
    return matched


class RuleBasedResumeClassifier(ResumeClassifier):
    """基于规则的简历分类器实现。

    通过技能/项目/工作关键词匹配技术方向，根据工作年限判定资历等级，
    从工作经历中推断行业背景。
    """

    @property
    def version(self) -> str:
        return "rule-classifier-v2"

    def classify(self, profile: CandidateProfile) -> ClassificationResult:
        # 从技能 + 项目技术栈 + 工作文本 构建匹配语料
        tokens, corpus = _build_search_corpus(profile)

        # 匹配技术方向
        tech_direction_tags = _match_directions(tokens, corpus)

        # 计算总工作年限
        total_years = _compute_total_years(profile.work_experiences)

        # 技术深度 = 技能分类数 + 技能总数
        unique_categories = {
            s.category for s in profile.skills if s.category
        }
        tech_depth = len(unique_categories) + len(profile.skills)

        return ClassificationResult(
            tech_direction_tags=sorted(set(tech_direction_tags)),
            experience_level=_experience_level(total_years),
            industry_tags=_extract_industry_tags(profile.work_experiences),
            stats={
                "total_years": total_years,
                "project_count": len(profile.projects),
                "tech_depth": tech_depth,
                "has_management": _has_management(profile.work_experiences),
            },
        )
