"""match-v1 policy fixture tests (RIP-013 §11)."""

from __future__ import annotations

import pytest

from backend.domain.match_assessment.policy import (
    DIMENSION_WEIGHTS,
    RECOMMENDATION_BANDS,
    SKILL_ALIASES,
    is_severe_years,
    normalize_skill,
    recommendation_for,
    weight,
)
from backend.domain.match_assessment.schemas import DIMENSION_KEYS


def test_weights_sum_to_100() -> None:
    assert sum(DIMENSION_WEIGHTS.values()) == 100


def test_weights_cover_exact_stable_key_set() -> None:
    assert set(DIMENSION_WEIGHTS) == set(DIMENSION_KEYS)
    assert len(DIMENSION_WEIGHTS) == 8


def test_exact_weights() -> None:
    assert DIMENSION_WEIGHTS == {
        "required_skills": 25,
        "experience_depth": 15,
        "project_evidence": 20,
        "responsibility_alignment": 15,
        "technical_stack": 10,
        "industry_context": 5,
        "basic_conditions": 5,
        "preferred_qualifications": 5,
    }


def test_weight_returns_per_key() -> None:
    assert weight("required_skills") == 25
    assert weight("preferred_qualifications") == 5


def test_cap_ordering_invariant() -> None:
    from backend.domain.match_assessment.policy import CORE_SKILLS_CAP, SEVERE_YEARS_CAP

    assert CORE_SKILLS_CAP > SEVERE_YEARS_CAP
    assert CORE_SKILLS_CAP == 75.0
    assert SEVERE_YEARS_CAP == 70.0


def test_recommendation_bands_advisory_labels() -> None:
    assert RECOMMENDATION_BANDS == [
        (80.0, "strong_hire"),
        (60.0, "hire"),
        (40.0, "conditional"),
        (0.0, "reject"),
    ]
    assert [threshold for threshold, _ in RECOMMENDATION_BANDS] == [80.0, 60.0, 40.0, 0.0]


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100.0, "strong_hire"),
        (80.0, "strong_hire"),
        (79.99, "hire"),
        (60.0, "hire"),
        (59.99, "conditional"),
        (40.0, "conditional"),
        (39.99, "reject"),
        (0.0, "reject"),
    ],
)
def test_recommendation_band_boundaries(score: float, expected: str) -> None:
    assert recommendation_for(score) == expected


def test_normalize_skill_strips_and_lowers() -> None:
    assert normalize_skill("  Python ") == "python"
    assert normalize_skill("React.js") == "react"


def test_normalize_skill_aliases() -> None:
    assert normalize_skill("JS") == "javascript"
    assert normalize_skill("Node") == "nodejs"
    assert normalize_skill("C#") == "csharp"
    assert normalize_skill("C++") == "cpp"
    assert normalize_skill("K8s") == "k8s"
    assert normalize_skill("vue.js") == "vuejs"


def test_normalize_skill_unknown_passes_through() -> None:
    assert normalize_skill("golang") == "go"
    assert normalize_skill("haskell") == "haskell"


def test_alias_table_is_deterministic_normalization() -> None:
    # every alias value is itself normalized (stable fixed point)
    for raw, canonical in SKILL_ALIASES.items():
        assert normalize_skill(canonical) == canonical, raw


@pytest.mark.parametrize(
    ("required_years", "evidenced_years", "expected"),
    [
        (3, 1.7, True),
        (3, 1.79, True),
        (3, 1.8, False),
        (3, 2.0, False),
        (3, None, False),
        (5, 2.9, True),
        (5, 3.0, False),
        (2, 1.0, False),
        (2, 0.0, False),
        (1, 0.0, False),
        (4, 2.39, True),
        (4, 2.4, False),
    ],
)
def test_severe_years_boundaries(
    required_years: int, evidenced_years: float | None, expected: bool
) -> None:
    assert is_severe_years(required_years=required_years, evidenced_years=evidenced_years) is expected


def test_severe_years_unknown_evidence_is_not_severe() -> None:
    # unknown years must fall through to evidence_gap, never the cap
    assert is_severe_years(required_years=10, evidenced_years=None) is False


def test_fixture_validates_at_import() -> None:
    # The policy module raises at import when inconsistent; importing it here
    # proves the fixture is currently consistent.
    import backend.domain.match_assessment.policy as policy

    policy._validate_fixture()
