"""Pure hybrid JD matching policy tests."""

from __future__ import annotations

from backend.domain.jd.matching_v2 import (
    DimensionScore,
    DimensionStatus,
    HardFilterStatus,
    JDHardRequirement,
    aggregate_dimensions,
    evaluate_hard_requirements,
)


def test_hard_filter_unknown_is_not_failure() -> None:
    results = evaluate_hard_requirements(
        [JDHardRequirement(id="JD-HARD-001", type="required_skill", value="Python", evidence_id="JD-SKILL-001")],
        profile={"skills": []},
        facts=[],
    )
    assert results[0].status == HardFilterStatus.UNKNOWN
    assert results[0].human_confirmation_required is False


def test_hard_filter_fail_requires_human_confirmation() -> None:
    results = evaluate_hard_requirements(
        [JDHardRequirement(id="JD-HARD-001", type="required_skill", value="Go", evidence_id="JD-SKILL-001")],
        profile={"skills": [{"name": "Python"}]},
        facts=[],
    )
    assert results[0].status == HardFilterStatus.FAIL
    aggregate = aggregate_dimensions(results, [])
    assert aggregate.match_score is None
    assert aggregate.recommendation == "hard_filter_review"
    assert aggregate.human_confirmation_required is True


def test_aggregate_normalizes_known_dimensions_and_manual_review_low_coverage() -> None:
    dimensions = [
        DimensionScore(
            dimension="skill_fit", weight=30, score=80,
            status=DimensionStatus.SUPPORTED, reason="ok", confidence=0.8,
        ),
        DimensionScore(
            dimension="responsibility_fit", weight=20, score=70,
            status=DimensionStatus.PARTIAL, reason="ok", confidence=0.6,
        ),
        DimensionScore(
            dimension="domain_fit", weight=50, score=None,
            status=DimensionStatus.UNKNOWN, reason="missing", confidence=0.1,
        ),
    ]
    result = aggregate_dimensions([], dimensions)
    assert result.match_score is None
    assert result.recommendation == "manual_review"
    assert result.coverage == 0.5
