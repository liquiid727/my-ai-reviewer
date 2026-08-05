"""Pure `match-v1` scoring and deterministic gap engine (RIP-013 §6.3, §6.4).

The engine takes validated rule facts plus semantic dimension estimates and
returns an immutable result. It knows nothing about SQLAlchemy, Celery, LLM
providers, or HTTP: the semantic classifier's raw scores arrive as inputs,
and the engine owns only deterministic math — weighted totals, two-decimal
rounding, caps, and primary gap classification.
"""

from __future__ import annotations

from typing import Callable, Literal

from backend.domain.match_assessment.policy import (
    DIMENSION_KEYS,
    POLICY_VERSION,
    MatchPolicyError,
    recommendation_for,
    weight,
)
from backend.domain.match_assessment.schemas import (
    CapInput,
    DimensionInput,
    DimensionScore,
    GapCategory,
    GapInput,
    MatchV1Input,
    MatchV1Result,
    RequirementGap,
)


# The engine's default classifier implements the spec rule: when the semantic
# adapter marks a classification uncertain, evidence_gap wins (RIP-013 §6.4).
# The constrained semantic adapter (issue #108) may supply its own resolver
# via `classify`.
def _uncertain_wins(gap: GapInput) -> GapCategory:
    return "evidence_gap" if gap.uncertain else gap.category


_ACTION_TYPES: dict[GapCategory, Literal["review", "probe", "verify", "screen"]] = {
    "capability_gap": "screen",
    "expression_gap": "review",
    "evidence_gap": "probe",
    "hard_constraint_risk": "screen",
}


def _evidence_summary(dimension_inputs: list[DimensionInput]) -> dict[str, int]:
    summary: dict[str, int] = {"jd_evidence": 0, "resume_evidence": 0}
    for item in dimension_inputs:
        summary["jd_evidence"] += len(item.cited_jd_evidence)
        summary["resume_evidence"] += len(item.cited_resume_evidence)
    return summary


def _total_confidence(dimension_inputs: list[DimensionInput]) -> float:
    if not dimension_inputs:
        return 0.0
    return round(sum(item.confidence for item in dimension_inputs) / len(dimension_inputs), 3)


def _aggregate(dimension_inputs: list[DimensionInput]) -> dict[str, DimensionScore]:
    by_key: dict[str, DimensionScore] = {}
    for key in DIMENSION_KEYS:
        by_key[key] = DimensionScore(
            key=key,
            weight=weight(key),
            raw_score=0.0,
            weighted_points=0.0,
            confidence=0.0,
        )
    for item in dimension_inputs:
        score = by_key[item.key]
        score.weighted_points = round(item.raw_score * weight(item.key) / 100.0, 2)
        score.raw_score = item.raw_score
        score.confidence = item.confidence
        score.cited_jd_evidence = list(item.cited_jd_evidence)
        score.cited_resume_evidence = list(item.cited_resume_evidence)
        score.explanation = item.explanation
    return by_key


def _base_score(dimension_inputs: list[DimensionInput]) -> float:
    if not dimension_inputs:
        return 0.0
    return round(sum(item.raw_score * weight(item.key) / 100.0 for item in dimension_inputs), 2)


def _caps_applied(caps: list[CapInput]) -> list[Literal["core_skills", "severe_years"]]:
    applied = [cap.cap for cap in caps]
    return list(dict.fromkeys(applied))


def _gaps(
    gaps: list[GapInput],
    classify: Callable[[GapInput], GapCategory],
) -> list[RequirementGap]:
    out: list[RequirementGap] = []
    seen: set[str] = set()
    for gap in gaps:
        if gap.requirement_id in seen:
            continue
        seen.add(gap.requirement_id)
        category = classify(gap) if gap.uncertain else gap.category
        out.append(
            RequirementGap(
                requirement_id=gap.requirement_id,
                category=category,
                severity=gap.severity,
                candidate_evidence=list(gap.candidate_evidence),
                missing_evidence=gap.missing_evidence,
                confidence=gap.confidence,
                action_type=_ACTION_TYPES[category],
            )
        )
    return out


def evaluate(
    inputs: MatchV1Input | None = None,
    *,
    dimension_inputs: list[DimensionInput] | None = None,
    caps: list[CapInput] | None = None,
    gaps: list[GapInput] | None = None,
    classify: Callable[[GapInput], GapCategory] | None = None,
) -> MatchV1Result:
    """Score the dimension inputs and persist every applied cap.

    `classify` resolves uncertain gaps to a primary category. Without a custom
    classifier the semantic adapter's own category stands; deterministic rule
    facts carry `uncertain=False` and their category is recorded as-is.
    """
    if inputs is not None:
        dimension_inputs = inputs.dimension_inputs
        caps = inputs.caps
        gaps = inputs.gaps
    dimension_inputs = dimension_inputs or []
    caps = caps or []
    gaps = gaps or []

    unknown = set(DIMENSION_KEYS) - {item.key for item in dimension_inputs}
    if unknown:
        raise MatchPolicyError(f"match-v1 requires a score for every dimension, missing: {sorted(unknown)}")

    by_key = _aggregate(dimension_inputs)
    score_before = _base_score(dimension_inputs)

    if caps:
        # The lowest applicable cap wins: 75 for any missing core skill,
        # 70 for a severe years gap. Capped at 70 → also capped at 75 by
        # definition, so applying both caps must keep 70.
        cap_values = [75.0 if cap.cap == "core_skills" else 70.0 for cap in caps]
        score = round(min(score_before, min(cap_values)), 2)
    else:
        score = score_before

    classify = classify or _uncertain_wins
    return MatchV1Result(
        policy_version=POLICY_VERSION,
        total_score=score,
        score_before_caps=score_before,
        caps_applied=_caps_applied(caps),
        dimensions=[by_key[key] for key in DIMENSION_KEYS],
        gaps=_gaps(gaps, classify),
        recommendation=recommendation_for(score),
        overall_confidence=_total_confidence(dimension_inputs),
        evidence_summary=_evidence_summary(dimension_inputs),
        deterministic=True,
    )
