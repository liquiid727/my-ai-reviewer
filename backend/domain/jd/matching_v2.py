"""Versioned JD matching contracts and pure policy for hybrid_v2."""

from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.domain.jd.policies import norm_skill

MATCHER_VERSION = "hybrid-v2.0"
HARD_FILTER_POLICY_VERSION = "hard-filter-v1"
MATCH_SCHEMA_VERSION = "2"
MATCH_PROMPT_VERSION = "jd-match-v2"


class MatchStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"
    STALE = "stale"


class MatchMode(StrEnum):
    RULES_V1 = "rules_v1"
    HYBRID_V2 = "hybrid_v2"


class HardRequirementType(StrEnum):
    REQUIRED_SKILL = "required_skill"
    MINIMUM_EXPERIENCE_YEARS = "minimum_experience_years"
    REQUIRED_CERTIFICATE = "required_certificate"
    LOCATION_CONSTRAINT = "location_constraint"
    WORK_AUTHORIZATION = "work_authorization"


class HardRequirementOperator(StrEnum):
    PRESENT = "present"
    AT_LEAST = "at_least"
    MATCH = "match"


class HardFilterStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class DimensionStatus(StrEnum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


class MatchRecommendation(StrEnum):
    STRONG_MATCH = "strong_match"
    MATCH = "match"
    CONDITIONAL = "conditional"
    WEAK_MATCH = "weak_match"
    MANUAL_REVIEW = "manual_review"
    HARD_FILTER_REVIEW = "hard_filter_review"


class StaleReason(StrEnum):
    JD_REVISION_CHANGED = "jd_revision_changed"
    RESUME_FACTS_REVISION_CHANGED = "resume_facts_revision_changed"
    PROFILE_REVISION_CHANGED = "profile_revision_changed"
    MATCHER_VERSION_CHANGED = "matcher_version_changed"
    HARD_FILTER_POLICY_CHANGED = "hard_filter_policy_changed"
    PROMPT_OR_SCHEMA_CHANGED = "prompt_or_schema_changed"
    MODEL_CHANGED = "model_changed"
    RESULT_FAILED_OR_INCOMPLETE = "result_failed_or_incomplete"


class JDEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=500)
    field: str | None = Field(default=None, max_length=80)


class JDHardRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    type: HardRequirementType
    operator: HardRequirementOperator = HardRequirementOperator.PRESENT
    value: str | int | float
    evidence_id: str = Field(min_length=1, max_length=100)
    enforceable: bool = True


class SourceCatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    source: Literal["jd", "resume_fact", "candidate_profile", "match"]
    kind: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=300)
    excerpt: str = Field(min_length=1, max_length=500)
    page: int | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class HardFilterResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_id: str
    type: HardRequirementType
    status: HardFilterStatus
    reason: str
    jd_evidence_ids: list[str] = Field(default_factory=list)
    candidate_evidence_ids: list[str] = Field(default_factory=list)
    human_confirmation_required: bool = False


class DimensionScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: str
    weight: int = Field(ge=0, le=100)
    score: float | None = Field(default=None, ge=0, le=100)
    status: DimensionStatus
    reason: str = Field(min_length=1, max_length=1000)
    jd_evidence_ids: list[str] = Field(default_factory=list)
    candidate_evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)

    @field_validator("score")
    @classmethod
    def _unknown_score_is_nullable(cls, value: float | None) -> float | None:
        return round(value, 1) if value is not None else None


class HybridMatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_score: float | None = Field(default=None, ge=0, le=100)
    recommendation: MatchRecommendation
    human_confirmation_required: bool = False
    hard_filters: list[HardFilterResult] = Field(default_factory=list)
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    evidence: list[SourceCatalogEntry] = Field(default_factory=list)
    coverage: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    detail: str | None = None


DIMENSION_WEIGHTS: dict[str, int] = {
    "skill_fit": 30,
    "responsibility_fit": 20,
    "relevant_experience": 15,
    "seniority_scope": 10,
    "project_evidence": 10,
    "engineering_architecture": 10,
    "domain_fit": 5,
}


def stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def fingerprint_payload(value: object) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def _contains_normalized(value: str, haystack: list[str]) -> bool:
    needle = norm_skill(value)
    return any(needle == norm_skill(item) or (len(needle) >= 4 and needle in norm_skill(item)) for item in haystack)


def _candidate_skills(profile: dict[str, Any], facts: list[dict[str, Any]]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for index, skill in enumerate(profile.get("skills") or [], 1):
        if isinstance(skill, dict) and skill.get("name"):
            rows.append((str(skill["name"]), f"CAND-SKILL-{index:03d}"))
        elif isinstance(skill, str):
            rows.append((skill, f"CAND-SKILL-{index:03d}"))
    for index, fact in enumerate(facts, 1):
        if str(fact.get("fact_type", "")).lower() == "skill":
            rows.append((str(fact.get("fact_key") or fact.get("key") or ""), f"CAND-FACT-{index:03d}"))
    return [(name, evidence_id) for name, evidence_id in rows if name]


def _candidate_years(profile: dict[str, Any], facts: list[dict[str, Any]]) -> tuple[float | None, list[str]]:
    values: list[float] = []
    evidence_ids: list[str] = []
    for index, exp in enumerate(profile.get("work_experiences") or [], 1):
        if not isinstance(exp, dict):
            continue
        for key in ("years", "duration_years", "experience_years"):
            if isinstance(exp.get(key), (int, float)):
                values.append(float(exp[key]))
                evidence_ids.append(f"CAND-WORK-{index:03d}")
    for index, fact in enumerate(facts, 1):
        value = fact.get("fact_value") or fact.get("value") or {}
        if isinstance(value, dict):
            for key in ("years", "duration_years", "experience_years"):
                if isinstance(value.get(key), (int, float)):
                    values.append(float(value[key]))
                    evidence_ids.append(f"CAND-FACT-{index:03d}")
    return (max(values), evidence_ids) if values else (None, [])


def evaluate_hard_requirements(
    requirements: list[JDHardRequirement],
    *,
    profile: dict[str, Any],
    facts: list[dict[str, Any]],
) -> list[HardFilterResult]:
    skill_rows = _candidate_skills(profile, facts)
    skill_names = [name for name, _ in skill_rows]
    certificates = [
        str(item.get("name") if isinstance(item, dict) else item)
        for item in (profile.get("certificates") or [])
        if item
    ]
    years, year_evidence = _candidate_years(profile, facts)
    results: list[HardFilterResult] = []
    for req in requirements:
        jd_ids = [req.evidence_id]
        candidate_ids: list[str] = []
        status = HardFilterStatus.UNKNOWN
        reason = "No candidate evidence was available."
        if not req.enforceable:
            status = HardFilterStatus.UNKNOWN
            reason = "Requirement is not enforceable by deterministic policy."
        elif req.type == HardRequirementType.REQUIRED_SKILL:
            if _contains_normalized(str(req.value), skill_names):
                status = HardFilterStatus.PASS
                candidate_ids = [
                    evidence_id for name, evidence_id in skill_rows if _contains_normalized(str(req.value), [name])
                ]
                reason = "Candidate has matching skill evidence."
            elif skill_names:
                status = HardFilterStatus.FAIL
                reason = "Candidate skill evidence conflicts with the explicit required skill."
        elif req.type == HardRequirementType.MINIMUM_EXPERIENCE_YEARS:
            required_years = float(req.value)
            if years is None:
                status = HardFilterStatus.UNKNOWN
            elif years >= required_years:
                status = HardFilterStatus.PASS
                candidate_ids = year_evidence
                reason = "Candidate meets the minimum experience requirement."
            else:
                status = HardFilterStatus.FAIL
                candidate_ids = year_evidence
                reason = "Candidate has explicit experience evidence below the minimum."
        elif req.type == HardRequirementType.REQUIRED_CERTIFICATE:
            if _contains_normalized(str(req.value), certificates):
                status = HardFilterStatus.PASS
                candidate_ids = ["CAND-CERT-001"]
                reason = "Candidate has the required certificate."
            elif certificates:
                status = HardFilterStatus.FAIL
                reason = "Candidate certificate evidence does not include the required certificate."
        elif req.type in {HardRequirementType.LOCATION_CONSTRAINT, HardRequirementType.WORK_AUTHORIZATION}:
            # These facts are often absent in masked profiles. Only fail on an explicit conflict.
            searchable = stable_json({"profile": profile, "facts": facts}).casefold()
            value = str(req.value).casefold()
            if value and value in searchable:
                status = HardFilterStatus.PASS
                candidate_ids = ["CAND-PROFILE-001"]
                reason = "Candidate evidence explicitly satisfies the requirement."
            else:
                status = HardFilterStatus.UNKNOWN
                reason = "No explicit candidate evidence was available for this requirement."
        results.append(
            HardFilterResult(
                requirement_id=req.id,
                type=req.type,
                status=status,
                reason=reason,
                jd_evidence_ids=jd_ids,
                candidate_evidence_ids=sorted(set(candidate_ids)),
                human_confirmation_required=status == HardFilterStatus.FAIL,
            )
        )
    return results


def aggregate_dimensions(
    hard_filters: list[HardFilterResult],
    dimensions: list[DimensionScore],
) -> HybridMatchResult:
    known_weight = sum(d.weight for d in dimensions if d.score is not None and d.status != DimensionStatus.UNKNOWN)
    total_weight = sum(d.weight for d in dimensions)
    coverage = round(known_weight / total_weight, 3) if total_weight else 0.0
    hard_fail = any(item.status == HardFilterStatus.FAIL for item in hard_filters)
    hard_unknown = any(item.status == HardFilterStatus.UNKNOWN for item in hard_filters)
    human_confirmation = hard_fail
    if hard_fail:
        score = None
        recommendation = MatchRecommendation.HARD_FILTER_REVIEW
    elif coverage < 0.6 or hard_unknown:
        score = None
        recommendation = MatchRecommendation.MANUAL_REVIEW
    else:
        weighted = sum((d.score or 0) * d.weight for d in dimensions if d.score is not None)
        score = round(weighted / known_weight, 1) if known_weight else None
        if score is None:
            recommendation = MatchRecommendation.MANUAL_REVIEW
        elif score >= 80:
            recommendation = MatchRecommendation.STRONG_MATCH
        elif score >= 65:
            recommendation = MatchRecommendation.MATCH
        elif score >= 50:
            recommendation = MatchRecommendation.CONDITIONAL
        else:
            recommendation = MatchRecommendation.WEAK_MATCH
    confidence_values = [d.confidence for d in dimensions if d.score is not None]
    confidence = round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else 0.0
    return HybridMatchResult(
        match_score=score,
        recommendation=recommendation,
        human_confirmation_required=human_confirmation,
        hard_filters=hard_filters,
        dimension_scores=dimensions,
        evidence=[],
        coverage=coverage,
        confidence=confidence,
        detail=_summary_detail(score, recommendation, coverage, hard_filters),
    )


def validate_dimension_evidence(dimensions: list[DimensionScore], catalog: list[SourceCatalogEntry]) -> None:
    catalog_ids = {entry.id for entry in catalog}
    seen_refs: set[str] = set()
    for dimension in dimensions:
        for evidence_id in [*dimension.jd_evidence_ids, *dimension.candidate_evidence_ids]:
            if evidence_id not in catalog_ids:
                raise ValueError(f"Unknown evidence id: {evidence_id}")
            key = f"{dimension.dimension}:{evidence_id}"
            if key in seen_refs:
                raise ValueError(f"Duplicate evidence id in dimension: {evidence_id}")
            seen_refs.add(key)


def extract_hard_requirements_from_jd(jd: object) -> list[JDHardRequirement]:
    requirements: list[JDHardRequirement] = []
    stored = getattr(jd, "hard_requirements", None) or []
    if stored:
        return [JDHardRequirement.model_validate(item) for item in stored]
    for index, skill in enumerate(getattr(jd, "required_skills", None) or [], 1):
        if isinstance(skill, dict):
            name = str(skill.get("name") or "").strip()
            critical = bool(skill.get("critical"))
        else:
            name = str(skill).strip()
            critical = False
        if not name:
            continue
        requirements.append(
            JDHardRequirement(
                id=f"JD-HARD-{index:03d}",
                type=HardRequirementType.REQUIRED_SKILL,
                operator=HardRequirementOperator.PRESENT,
                value=name,
                evidence_id=f"JD-SKILL-{index:03d}",
                enforceable=critical,
            )
        )
    return requirements


def build_input_fingerprint(parts: dict[str, object]) -> str:
    return fingerprint_payload(parts)


def _summary_detail(
    score: float | None,
    recommendation: MatchRecommendation,
    coverage: float,
    hard_filters: list[HardFilterResult],
) -> str:
    hard_failures = [item.requirement_id for item in hard_filters if item.status == HardFilterStatus.FAIL]
    if hard_failures:
        return f"Hard filter review required for {', '.join(hard_failures)}."
    if score is None:
        return f"Manual review required; evidence coverage is {coverage:.0%}."
    readable = re.sub(r"_", " ", recommendation.value)
    return f"Hybrid match score {score}/100 with {coverage:.0%} evidence coverage; recommendation: {readable}."


__all__ = [
    "DIMENSION_WEIGHTS",
    "HARD_FILTER_POLICY_VERSION",
    "MATCHER_VERSION",
    "MATCH_PROMPT_VERSION",
    "MATCH_SCHEMA_VERSION",
    "DimensionScore",
    "DimensionStatus",
    "HardFilterResult",
    "HardFilterStatus",
    "HardRequirementOperator",
    "HardRequirementType",
    "HybridMatchResult",
    "JDHardRequirement",
    "JDEvidenceItem",
    "MatchMode",
    "MatchRecommendation",
    "MatchStatus",
    "SourceCatalogEntry",
    "StaleReason",
    "aggregate_dimensions",
    "build_input_fingerprint",
    "evaluate_hard_requirements",
    "extract_hard_requirements_from_jd",
    "fingerprint_payload",
    "stable_json",
    "validate_dimension_evidence",
]
