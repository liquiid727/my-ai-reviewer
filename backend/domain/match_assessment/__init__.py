"""Match Assessment domain (RIP-013).

Pure, versioned `match-v1` scoring policy, Source Catalog normalization, and
deterministic gap engine. The package must stay free of SQLAlchemy, Celery,
LLM providers, and HTTP: it consumes validated inputs and returns immutable
results that the application layer persists.
"""

from backend.domain.match_assessment.engine import evaluate
from backend.domain.match_assessment.policy import (
    CORE_SKILLS_CAP,
    DIMENSION_WEIGHTS,
    POLICY_VERSION,
    RECOMMENDATION_BANDS,
    SEVERE_YEARS_CAP,
    SEVERE_YEARS_MIN_REQUIRED,
    SEVERE_YEARS_RATIO,
    SKILL_ALIASES,
    MatchPolicyError,
    is_severe_years,
    normalize_skill,
    recommendation_for,
    weight,
)
from backend.domain.match_assessment.schemas import (
    CapInput,
    CapKey,
    DimensionInput,
    DimensionKey,
    DimensionScore,
    GapCategory,
    GapInput,
    HardConstraintKey,
    MatchV1Input,
    MatchV1Result,
    RequirementGap,
    RuleResult,
    SourceCatalog,
    SourceCatalogItem,
)
from backend.domain.match_assessment.source_catalog import build_catalog

__all__ = [
    "CORE_SKILLS_CAP",
    "CapInput",
    "CapKey",
    "DIMENSION_WEIGHTS",
    "DimensionInput",
    "DimensionKey",
    "DimensionScore",
    "GapCategory",
    "GapInput",
    "HardConstraintKey",
    "MatchPolicyError",
    "MatchV1Input",
    "MatchV1Result",
    "POLICY_VERSION",
    "RECOMMENDATION_BANDS",
    "RequirementGap",
    "RuleResult",
    "SEVERE_YEARS_CAP",
    "SEVERE_YEARS_MIN_REQUIRED",
    "SEVERE_YEARS_RATIO",
    "SKILL_ALIASES",
    "SourceCatalog",
    "SourceCatalogItem",
    "build_catalog",
    "evaluate",
    "is_severe_years",
    "normalize_skill",
    "recommendation_for",
    "weight",
]
