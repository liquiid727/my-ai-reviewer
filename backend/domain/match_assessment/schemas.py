"""Match Assessment domain schemas (RIP-013 §6)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DimensionKey = Literal[
    "required_skills",
    "experience_depth",
    "project_evidence",
    "responsibility_alignment",
    "technical_stack",
    "industry_context",
    "basic_conditions",
    "preferred_qualifications",
]

CapKey = Literal["core_skills", "severe_years"]

GapCategory = Literal[
    "capability_gap",
    "expression_gap",
    "evidence_gap",
    "hard_constraint_risk",
]

HardConstraintKey = Literal[
    "education",
    "location",
    "certification",
    "work_authorization",
    "language",
    "years",
]

DIMENSION_KEYS: tuple[DimensionKey, ...] = (
    "required_skills",
    "experience_depth",
    "project_evidence",
    "responsibility_alignment",
    "technical_stack",
    "industry_context",
    "basic_conditions",
    "preferred_qualifications",
)


class SourceCatalogItem(BaseModel):
    """One stable evidence item the LLM may cite (RIP-013 §6.2)."""

    id: str = Field(min_length=1, max_length=120)
    kind: Literal["requirement", "responsibility", "fact", "project", "profile"]
    claim: str = Field(min_length=1, max_length=500)
    masked_excerpt: str | None = Field(default=None, max_length=500)
    provenance: Literal["source", "llm", "manual"] = "source"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class SourceCatalog(BaseModel):
    """Typed evidence catalog for one assessment run (RIP-013 §6.2).

    IDs follow `jd:<version>:requirement:<key>` / `resume:<version>:fact:<key>`
    shapes so the constrained classifier can cite only these identifiers.
    """

    items: list[SourceCatalogItem] = Field(default_factory=list, max_length=500)

    def by_id(self, item_id: str) -> SourceCatalogItem | None:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def ids(self) -> set[str]:
        return {item.id for item in self.items}


class RuleResult(BaseModel):
    """Deterministic rule outcome for one requirement (RIP-013 §6.3/§6.4)."""

    requirement_id: str
    rule: str = "match-v1"
    outcome: bool
    reason: str | None = None


class DimensionScore(BaseModel):
    """One weighted dimension result (RIP-013 §6.3)."""

    key: DimensionKey
    weight: int = Field(ge=0, le=100)
    raw_score: float = Field(ge=0.0, le=100.0)
    weighted_points: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    cited_jd_evidence: list[str] = Field(default_factory=list)
    cited_resume_evidence: list[str] = Field(default_factory=list)
    rule_results: list[RuleResult] = Field(default_factory=list)
    explanation: str | None = None


class RequirementGap(BaseModel):
    """Primary gap classification for one JD requirement (RIP-013 §6.4)."""

    requirement_id: str
    category: GapCategory
    severity: Literal["low", "medium", "high"]
    candidate_evidence: list[str] = Field(default_factory=list)
    missing_evidence: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    action_type: Literal["review", "probe", "verify", "screen"] = "review"


class MatchV1Result(BaseModel):
    """Immutable completed engine result for policy `match-v1`."""

    policy_version: str = "match-v1"
    schema_version: str = "match-v1-result"
    total_score: float = Field(ge=0.0, le=100.0)
    score_before_caps: float = Field(ge=0.0, le=100.0)
    caps_applied: list[CapKey] = Field(default_factory=list)
    dimensions: list[DimensionScore] = Field(default_factory=list)
    gaps: list[RequirementGap] = Field(default_factory=list)
    recommendation: str = "conditional"
    overall_confidence: float = Field(ge=0.0, le=1.0)
    evidence_summary: dict[str, int] = Field(default_factory=dict)
    deterministic: bool = False


class CapInput(BaseModel):
    """Deterministic cap fact: a missing core skill or a severe years gap."""

    cap: CapKey
    reason: str | None = None


class GapInput(BaseModel):
    """Deterministic gap evidence for one JD requirement (RIP-013 §6.4).

    Classification is the semantic adapter's job; the engine only *records*
    the primary category it was given, defaulting to `evidence_gap` when the
    adapter marks the classification uncertain, and derives the action type.
    """

    requirement_id: str
    category: GapCategory
    severity: Literal["low", "medium", "high"]
    candidate_evidence: list[str] = Field(default_factory=list)
    missing_evidence: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    uncertain: bool = False


class DimensionInput(BaseModel):
    """One dimension's semantic raw score plus cited evidence IDs.

    The raw score is the classifier's direct estimate. It is not normalized
    here; callers must enforce [0, 100] on the boundary (Pydantic clamps).
    """

    key: DimensionKey
    raw_score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    cited_jd_evidence: list[str] = Field(default_factory=list)
    cited_resume_evidence: list[str] = Field(default_factory=list)
    explanation: str | None = None


class MatchV1Input(BaseModel):
    """Validated engine inputs: rule facts plus semantic dimension estimates."""

    policy_version: str = "match-v1"
    dimension_inputs: list[DimensionInput] = Field(default_factory=list, max_length=8)
    caps: list[CapInput] = Field(default_factory=list, max_length=8)
    gaps: list[GapInput] = Field(default_factory=list, max_length=200)
    deterministic: bool = True
