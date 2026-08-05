"""Pure match-v1 engine tests (RIP-013 §6.3/§6.4)."""

from __future__ import annotations

import pytest

from backend.domain.match_assessment.engine import evaluate
from backend.domain.match_assessment.policy import MatchPolicyError
from backend.domain.match_assessment.schemas import (
    CapInput,
    DimensionInput,
    DimensionKey,
    GapInput,
    MatchV1Input,
)

_WEIGHTS: dict[DimensionKey, int] = {
    "required_skills": 25,
    "experience_depth": 15,
    "project_evidence": 20,
    "responsibility_alignment": 15,
    "technical_stack": 10,
    "industry_context": 5,
    "basic_conditions": 5,
    "preferred_qualifications": 5,
}


def _dimension(key: DimensionKey, raw: float, confidence: float = 1.0) -> DimensionInput:
    return DimensionInput(key=key, raw_score=raw, confidence=confidence)


def _all(raw: float, confidence: float = 1.0) -> list[DimensionInput]:
    return [_dimension(key, raw, confidence) for key in _WEIGHTS]


def test_perfect_score_is_100() -> None:
    result = evaluate(dimension_inputs=_all(100.0))
    assert result.total_score == 100.0
    assert result.score_before_caps == 100.0
    assert result.caps_applied == []
    assert result.recommendation == "strong_hire"
    assert result.deterministic is True


def test_weighted_totals_exact() -> None:
    inputs = [
        _dimension("required_skills", 100.0),  # 25.0
        _dimension("experience_depth", 100.0),  # 15.0
        _dimension("project_evidence", 50.0),  # 10.0
        _dimension("responsibility_alignment", 100.0),  # 15.0
        _dimension("technical_stack", 100.0),  # 10.0
        _dimension("industry_context", 100.0),  # 5.0
        _dimension("basic_conditions", 100.0),  # 5.0
        _dimension("preferred_qualifications", 0.0),  # 0.0
    ]
    result = evaluate(dimension_inputs=inputs)
    assert result.total_score == 85.0
    assert result.score_before_caps == 85.0


def test_weighted_totals_two_decimal_rounding() -> None:
    # 33.33 * 25/100 = 8.3325 → 8.33; rest zero → total 8.33
    result = evaluate(dimension_inputs=[_dimension("required_skills", 33.33)] + _all(0.0)[1:])
    assert result.total_score == 8.33
    assert result.score_before_caps == 8.33


def test_dimensions_aggregated_with_weights_and_points() -> None:
    result = evaluate(dimension_inputs=_all(50.0))
    assert len(result.dimensions) == 8
    by_key = {dim.key: dim for dim in result.dimensions}
    for key, expected_weight in _WEIGHTS.items():
        dim = by_key[key]
        assert dim.weight == expected_weight
        assert dim.raw_score == 50.0
        assert dim.weighted_points == round(50.0 * expected_weight / 100.0, 2)


def test_core_skill_cap_75() -> None:
    result = evaluate(
        dimension_inputs=_all(90.0),
        caps=[CapInput(cap="core_skills", reason="missing core skill: kubernetes")],
    )
    assert result.total_score == 75.0
    assert result.score_before_caps == 90.0
    assert result.caps_applied == ["core_skills"]
    assert result.recommendation == "hire"


def test_severe_years_cap_70() -> None:
    result = evaluate(
        dimension_inputs=_all(90.0),
        caps=[CapInput(cap="severe_years", reason="max evidenced years < 60% of 5y minimum")],
    )
    assert result.total_score == 70.0
    assert result.score_before_caps == 90.0
    assert result.caps_applied == ["severe_years"]
    assert result.recommendation == "hire"


def test_lowest_cap_wins() -> None:
    result = evaluate(
        dimension_inputs=_all(90.0),
        caps=[
            CapInput(cap="core_skills", reason="missing core skill"),
            CapInput(cap="severe_years", reason="severe years gap"),
        ],
    )
    assert result.total_score == 70.0
    assert result.caps_applied == ["core_skills", "severe_years"]


def test_caps_never_raise_the_score() -> None:
    result = evaluate(
        dimension_inputs=_all(40.0),
        caps=[CapInput(cap="core_skills", reason="missing core skill")],
    )
    assert result.total_score == 40.0
    assert result.caps_applied == ["core_skills"]


def test_unknown_years_no_cap_and_evidence_gap() -> None:
    # unknown years → evidence_gap; no severe-years cap may be applied
    result = evaluate(
        dimension_inputs=_all(80.0),
        gaps=[GapInput(requirement_id="jd:v1:requirement:years", category="evidence_gap", severity="medium")],
    )
    assert result.total_score == 80.0
    assert result.caps_applied == []
    gaps = result.gaps
    assert len(gaps) == 1
    assert gaps[0].category == "evidence_gap"
    assert gaps[0].requirement_id == "jd:v1:requirement:years"


def test_duplicate_gap_inputs_produce_one_primary_gap() -> None:
    result = evaluate(
        dimension_inputs=_all(80.0),
        gaps=[
            GapInput(requirement_id="jd:v1:requirement:sk-1", category="capability_gap", severity="high"),
            GapInput(requirement_id="jd:v1:requirement:sk-1", category="expression_gap", severity="low"),
        ],
    )
    assert len(result.gaps) == 1
    assert result.gaps[0].requirement_id == "jd:v1:requirement:sk-1"
    assert result.gaps[0].category == "capability_gap"


def test_uncertain_classification_resolves_to_evidence_gap() -> None:
    result = evaluate(
        dimension_inputs=_all(80.0),
        gaps=[
            GapInput(
                requirement_id="jd:v1:requirement:sk-2",
                category="capability_gap",
                severity="medium",
                uncertain=True,
            )
        ],
    )
    assert len(result.gaps) == 1
    assert result.gaps[0].category == "evidence_gap"
    assert result.gaps[0].action_type == "probe"


def test_semantic_category_stands_when_not_uncertain() -> None:
    result = evaluate(
        dimension_inputs=_all(80.0),
        gaps=[GapInput(requirement_id="jd:v1:requirement:sk-3", category="expression_gap", severity="low")],
    )
    assert result.gaps[0].category == "expression_gap"
    assert result.gaps[0].action_type == "review"


def test_hard_constraint_risk_action_screen() -> None:
    result = evaluate(
        dimension_inputs=_all(80.0),
        gaps=[GapInput(requirement_id="jd:v1:requirement:loc", category="hard_constraint_risk", severity="high")],
    )
    assert result.gaps[0].category == "hard_constraint_risk"
    assert result.gaps[0].action_type == "screen"


def test_capability_gap_action_screen() -> None:
    result = evaluate(
        dimension_inputs=_all(80.0),
        gaps=[GapInput(requirement_id="jd:v1:requirement:sk-4", category="capability_gap", severity="high")],
    )
    assert result.gaps[0].action_type == "screen"


def test_missing_dimension_raises() -> None:
    with pytest.raises(MatchPolicyError):
        evaluate(dimension_inputs=_all(80.0)[:7])


def test_input_container_matches_keyword_form() -> None:
    inputs = MatchV1Input(
        dimension_inputs=_all(100.0),
        caps=[CapInput(cap="core_skills")],
        gaps=[GapInput(requirement_id="r1", category="evidence_gap", severity="low")],
    )
    result = evaluate(inputs)
    assert result.total_score == 75.0
    assert result.caps_applied == ["core_skills"]
    assert result.gaps[0].requirement_id == "r1"


def test_evidence_summary_counts_unique_ids() -> None:
    inputs = [
        DimensionInput(
            key="required_skills",
            raw_score=90.0,
            confidence=1.0,
            cited_jd_evidence=["jd:r:1"],
            cited_resume_evidence=["res:f:1"],
        ),
        DimensionInput(
            key="experience_depth",
            raw_score=90.0,
            confidence=1.0,
            cited_jd_evidence=["jd:r:1"],
            cited_resume_evidence=["res:f:1"],
        ),
    ] + _all(90.0)[2:]
    result = evaluate(dimension_inputs=inputs)
    assert result.evidence_summary["jd_evidence"] == 2
    assert result.evidence_summary["resume_evidence"] == 2


def test_overall_confidence_is_mean_of_dimension_confidence() -> None:
    inputs = [
        _dimension("required_skills", 100.0, confidence=1.0),
        _dimension("experience_depth", 100.0, confidence=0.5),
        _dimension("project_evidence", 100.0, confidence=0.5),
        _dimension("responsibility_alignment", 100.0, confidence=0.5),
        _dimension("technical_stack", 100.0, confidence=0.5),
        _dimension("industry_context", 100.0, confidence=0.5),
        _dimension("basic_conditions", 100.0, confidence=0.5),
        _dimension("preferred_qualifications", 100.0, confidence=0.5),
    ]
    result = evaluate(dimension_inputs=inputs)
    assert result.overall_confidence == 0.562


def test_all_gap_categories_executable() -> None:
    result = evaluate(
        dimension_inputs=_all(80.0),
        gaps=[
            GapInput(requirement_id="jd:v1:requirement:g1", category="capability_gap", severity="high"),
            GapInput(requirement_id="jd:v1:requirement:g2", category="expression_gap", severity="low"),
            GapInput(requirement_id="jd:v1:requirement:g3", category="evidence_gap", severity="medium"),
            GapInput(requirement_id="jd:v1:requirement:g4", category="hard_constraint_risk", severity="high"),
        ],
    )
    assert [gap.category for gap in result.gaps] == [
        "capability_gap",
        "expression_gap",
        "evidence_gap",
        "hard_constraint_risk",
    ]
    assert [gap.action_type for gap in result.gaps] == ["screen", "review", "probe", "screen"]
