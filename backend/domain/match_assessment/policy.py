"""Versioned `match-v1` policy fixture (RIP-013 §6.3, §6.5).

The policy is a static, versioned fixture: weights sum to 100, the stable
dimension key set matches the schema, cap and recommendation thresholds are
explicit, and skill aliases are a deterministic normalization table. Import
raises at startup when the fixture is inconsistent, so a broken policy can
never be deployed silently.
"""

from __future__ import annotations

from backend.domain.match_assessment.schemas import DIMENSION_KEYS, DimensionKey

POLICY_VERSION = "match-v1"

# Eight stable dimensions with their exact weights (RIP-013 §6.3 table).
DIMENSION_WEIGHTS: dict[DimensionKey, int] = {
    "required_skills": 25,
    "experience_depth": 15,
    "project_evidence": 20,
    "responsibility_alignment": 15,
    "technical_stack": 10,
    "industry_context": 5,
    "basic_conditions": 5,
    "preferred_qualifications": 5,
}

# Caps (RIP-013 §6.3). The lowest applicable cap wins.
CORE_SKILLS_CAP = 75.0
SEVERE_YEARS_CAP = 70.0

# Severe-years definition: candidate's maximum evidenced relevant years are
# less than 60% of an explicit minimum of at least three years.
SEVERE_YEARS_MIN_REQUIRED = 3
SEVERE_YEARS_RATIO = 0.6

# Missing any policy-marked core required skill caps total at 75.
CORE_SKILLS_CAP_THRESHOLD = 0.0  # any missing core skill applies the cap

# Recommendation bands (advisory labels; never authorization guards).
RECOMMENDATION_BANDS: list[tuple[float, str]] = [
    (80.0, "strong_hire"),
    (60.0, "hire"),
    (40.0, "conditional"),
    (0.0, "reject"),
]

# Skill alias table for deterministic requirement/candidate normalization.
SKILL_ALIASES: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "node": "nodejs",
    "nodejs": "nodejs",
    "py": "python",
    "golang": "go",
    "c#": "csharp",
    "c++": "cpp",
    "reactjs": "react",
    "react.js": "react",
    "react": "react",
    "vue": "vuejs",
    "vue.js": "vuejs",
    "kubernetes": "k8s",
    "k8s": "k8s",
}


class MatchPolicyError(ValueError):
    """Policy fixture is inconsistent and must be fixed before deploy."""


def _validate_fixture() -> None:
    if set(DIMENSION_WEIGHTS) != set(DIMENSION_KEYS):
        raise MatchPolicyError(
            "match-v1 dimension keys do not match the schema key set"
        )
    if sum(DIMENSION_WEIGHTS.values()) != 100:
        raise MatchPolicyError(f"match-v1 weights sum to {sum(DIMENSION_WEIGHTS.values())}, expected 100")
    if CORE_SKILLS_CAP <= SEVERE_YEARS_CAP:
        raise MatchPolicyError("core-skills cap must be higher than the severe-years cap")
    if not (0.0 < SEVERE_YEARS_RATIO < 1.0):
        raise MatchPolicyError("severe-years ratio must be in (0, 1)")
    if SEVERE_YEARS_MIN_REQUIRED < 1:
        raise MatchPolicyError("severe-years minimum must be at least one year")
    bands = sorted(band for band, _ in RECOMMENDATION_BANDS)
    if bands != [0.0, 40.0, 60.0, 80.0]:
        raise MatchPolicyError("recommendation bands must be 0/40/60/80")
    if any(weight <= 0 for weight in DIMENSION_WEIGHTS.values()):
        raise MatchPolicyError("match-v1 weights must all be positive")


_validate_fixture()


def weight(key: DimensionKey) -> int:
    return DIMENSION_WEIGHTS[key]


def normalize_skill(text: str) -> str:
    """Deterministic skill normalization shared by rules and gap engine."""
    import re

    base = re.sub(r"[^a-z0-9+#.]", "", str(text).lower())
    return SKILL_ALIASES.get(base, base)


def recommendation_for(total_score: float) -> str:
    for threshold, label in RECOMMENDATION_BANDS:
        if total_score >= threshold:
            return label
    return "reject"


def is_severe_years(*, required_years: int, evidenced_years: float | None) -> bool:
    """Severe means max evidenced years < 60% of an explicit minimum >= 3y."""
    if evidenced_years is None:
        return False
    if required_years < SEVERE_YEARS_MIN_REQUIRED:
        return False
    return evidenced_years < SEVERE_YEARS_RATIO * required_years
