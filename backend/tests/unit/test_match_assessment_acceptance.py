"""RIP-013 match-engine acceptance gate — pure half (#111, §11-§12).

Closes replay acceptance: the maintained synthetic fixtures cover the exact
dimension/weight key set, and identical inputs replay to the identical
score, caps, gaps, explanations, and evidence summary (deterministic=true).
"""

from __future__ import annotations

from typing import Any

from backend.domain.match_assessment.engine import evaluate
from backend.domain.match_assessment.policy import DIMENSION_KEYS
from backend.domain.match_assessment.schemas import (
    DimensionInput,
    GapInput,
    SourceCatalog,
    SourceCatalogItem,
)
from backend.infrastructure.matchers import (
    ALLOWED_DIMENSIONS,
    MatchedDimension,
    MatchedGap,
    MatchSemanticResult,
)


def test_fixture_dimension_keys_match_weights() -> None:
    """Every dimension key has a weight; every weight key is a dimension."""
    from backend.domain.match_assessment.policy import DIMENSION_WEIGHTS

    assert set(DIMENSION_KEYS) == set(DIMENSION_WEIGHTS)
    assert len(DIMENSION_KEYS) == 8


def test_replay_same_inputs_same_result() -> None:
    """Replay of identical inputs yields an identical immutable result."""
    dimension_inputs = [
        DimensionInput(key=key, raw_score=80.0, confidence=0.9) for key in DIMENSION_KEYS
    ]
    gaps = [
        GapInput(
            requirement_id="jd:v1:requirement:sk-1",
            category="evidence_gap",
            severity="medium",
            candidate_evidence=["resume:v1:fact:skill-0"],
            missing_evidence=False,
            confidence=0.6,
            uncertain=False,
        )
    ]

    first = evaluate(dimension_inputs=dimension_inputs, gaps=gaps)
    second = evaluate(dimension_inputs=dimension_inputs, gaps=gaps)

    assert first == second
    assert first.total_score == second.total_score
    assert first.score_before_caps == second.score_before_caps
    assert first.caps_applied == second.caps_applied
    assert [g.model_dump() for g in first.gaps] == [g.model_dump() for g in second.gaps]
    assert first.deterministic is True


def _catalog() -> SourceCatalog:
    return SourceCatalog(
        items=[
            SourceCatalogItem(
                id="jd:v1:requirement:sk-1",
                kind="requirement",
                claim="Go",
                masked_excerpt="精通 Go",
                provenance="source",
                confidence=0.95,
            ),
            SourceCatalogItem(
                id="resume:v1:fact:skill-0",
                kind="fact",
                claim="go",
                masked_excerpt="Go 项目经验 4 年",
                provenance="source",
                confidence=0.9,
            ),
        ]
    )


def test_replay_catalog_through_engine_is_stable() -> None:
    """Same catalog + fake semantic output replay to the same completed result."""
    catalog = _catalog()
    semantic = MatchSemanticResult(
        dimensions=[
            MatchedDimension(
                key=key,
                raw_score=80.0,
                confidence=0.9,
                cited_jd_evidence=["jd:v1:requirement:sk-1"] if key == "required_skills" else [],
                cited_resume_evidence=["resume:v1:fact:skill-0"] if key == "required_skills" else [],
                explanation="masked summary",
            )
            for key in ALLOWED_DIMENSIONS
        ],
        gaps=[
            MatchedGap(
                requirement_id="jd:v1:requirement:sk-1",
                category="evidence_gap",
                severity="medium",
                candidate_evidence=["resume:v1:fact:skill-0"],
                missing_evidence=False,
                confidence=0.6,
                uncertain=False,
            )
        ],
        model_info="fake-model",
        deterministic=False,
    )
    allowed = catalog.ids()

    def run() -> tuple[Any, ...]:
        result = evaluate(
            dimension_inputs=[
                DimensionInput(
                    key=dim.key,
                    raw_score=dim.raw_score,
                    confidence=dim.confidence,
                    cited_jd_evidence=[e for e in dim.cited_jd_evidence if e in allowed],
                    cited_resume_evidence=[e for e in dim.cited_resume_evidence if e in allowed],
                    explanation=dim.explanation,
                )
                for dim in semantic.dimensions
            ],
            gaps=[
                GapInput(
                    requirement_id=gap.requirement_id,
                    category=gap.category,
                    severity=gap.severity,  # type: ignore[arg-type]
                    candidate_evidence=gap.candidate_evidence,
                    missing_evidence=gap.missing_evidence,
                    confidence=gap.confidence,
                    uncertain=gap.uncertain,
                )
                for gap in semantic.gaps
            ],
        )
        return (
            result.total_score,
            result.score_before_caps,
            tuple(result.caps_applied),
            result.recommendation,
            tuple(g.model_dump() for g in result.gaps),
            result.evidence_summary,
        )

    assert run() == run()
