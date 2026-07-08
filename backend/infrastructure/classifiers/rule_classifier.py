import re
from datetime import date

from backend.domain.resume.schemas import CandidateProfile, WorkExperience
from backend.infrastructure.classifiers.base import ClassificationResult, ResumeClassifier

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

MANAGEMENT_KEYWORDS: set[str] = {
    "manager", "lead", "director", "head", "vp", "chief",
    "team lead", "tech lead", "engineering manager",
    "management", "leading", "managed", "supervised",
}

_DATE_PATTERN = re.compile(r"(\d{4})[-/.](\d{1,2})")


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    m = _DATE_PATTERN.search(raw)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        month = max(1, min(month, 12))
        return date(year, month, 1)
    year_only = re.search(r"\d{4}", raw)
    if year_only:
        return date(int(year_only.group()), 1, 1)
    return None


def _compute_total_years(experiences: list[WorkExperience]) -> float:
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
    if total_years <= 2:
        return "Junior"
    if total_years <= 5:
        return "Mid"
    if total_years <= 9:
        return "Senior"
    return "Staff"


def _has_management(experiences: list[WorkExperience]) -> bool:
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

    @property
    def version(self) -> str:
        return "rule-classifier-v1"

    def classify(self, profile: CandidateProfile) -> ClassificationResult:
        skill_names = {s.name.lower().strip() for s in profile.skills}

        tech_direction_tags: list[str] = []
        for direction, keywords in TECH_DIRECTION_KEYWORDS.items():
            if skill_names & keywords:
                tech_direction_tags.append(direction)

        total_years = _compute_total_years(profile.work_experiences)

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
