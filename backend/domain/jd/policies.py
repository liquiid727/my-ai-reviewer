"""Pure JD domain policies (no I/O)."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from backend.domain.jd.enums import STRUCTURED_FIELD_NAMES
from backend.domain.jd.schemas import (
    DraftItem,
    GapItem,
    JDExtraction,
    JDMatchResult,
    RequiredSkill,
    ReviewDraft,
    RiskItem,
    SkillMatchItem,
)

# Common skill aliases for deterministic matching.
_ALIASES: dict[str, str] = {
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
    "vuejs": "vue",
    "vue.js": "vue",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "tf": "terraform",
    "ml": "machinelearning",
    "ai": "artificialintelligence",
}


class JDProcessingError(ValueError):
    """Expected processing failure whose message is safe to return to clients."""

    def __init__(self, message: str, code: int = 5003) -> None:
        super().__init__(message)
        self.code = code


def normalize_jd_text(raw_text: str) -> str:
    """Create the canonical duplicate-detection representation of JD body text."""
    normalized = unicodedata.normalize("NFKC", raw_text).replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\s+", " ", normalized).strip()


def content_hash(raw_text: str) -> str:
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


def extraction_values(extraction: JDExtraction) -> dict[str, object]:
    return {
        "title": extraction.title,
        "company": extraction.company,
        "location": extraction.location,
        "seniority": extraction.seniority,
        "responsibilities": extraction.responsibilities,
        "required_skills": [skill.model_dump() for skill in extraction.required_skills],
        "preferred_skills": [skill.model_dump() for skill in extraction.preferred_skills],
    }


def draft_from_extraction(
    extraction: JDExtraction,
    *,
    parser_version: str,
    model_name: str | None = None,
    schema_version: str = "jd-review-v1",
) -> ReviewDraft:
    """Project a raw LLM extraction into a RIP-011 review draft (RIP-011 §6.1).

    Items keep the extractor's source evidence with `source` provenance and a
    stable per-list key; missing evidence is `unavailable`, never fabricated.
    """
    return ReviewDraft(
        title=extraction.title,
        company=extraction.company,
        location=extraction.location,
        seniority=extraction.seniority,
        responsibilities=[
            DraftItem(
                key=f"res-{index}",
                value=value,
                evidence=value,
                evidence_status="available",
                confidence=1.0,
                provenance="source",
            )
            for index, value in enumerate(extraction.responsibilities)
        ],
        required_skills=[
            DraftItem(
                key=f"sk-{index}",
                value=skill.name,
                evidence=skill.evidence or skill.name,
                evidence_status="available" if skill.evidence else "unavailable",
                confidence=1.0,
                provenance="source",
                critical=skill.critical,
            )
            for index, skill in enumerate(extraction.required_skills)
        ],
        preferred_skills=[
            DraftItem(
                key=f"psk-{index}",
                value=skill.name,
                evidence=skill.evidence or skill.name,
                evidence_status="available" if skill.evidence else "unavailable",
                confidence=1.0,
                provenance="source",
                critical=skill.critical,
            )
            for index, skill in enumerate(extraction.preferred_skills)
        ],
        parser_version=parser_version,
        model_name=model_name,
        prompt_version=None,
        schema_version=schema_version,
        overall_confidence=1.0,
    )


def merged_extraction_values(
    *,
    field_sources: dict[str, str] | None,
    extraction: JDExtraction,
    overwrite_manual: bool,
) -> dict[str, object]:
    sources = dict(field_sources or {})
    values: dict[str, object] = {}
    for field, value in extraction_values(extraction).items():
        if field not in STRUCTURED_FIELD_NAMES:
            continue
        if sources.get(field) == "manual" and not overwrite_manual:
            continue
        values[field] = value
        sources[field] = "llm"
    values["field_sources"] = sources
    values["extraction_source"] = "llm"
    return values


def norm_skill(text: str) -> str:
    base = re.sub(r"[^a-z0-9+#.]", "", str(text).lower())
    return _ALIASES.get(base, base)


def _match_one(
    req_norm: str,
    candidate_norm: set[str],
    candidate_map: dict[str, dict[str, Any]],
) -> tuple[bool, str | None]:
    if req_norm in candidate_norm:
        return True, _evidence_for(req_norm, candidate_map)
    for c_norm in candidate_norm:
        if len(req_norm) >= 4 and (req_norm in c_norm or c_norm in req_norm):
            return True, _evidence_for(c_norm, candidate_map)
    return False, None


def _evidence_for(norm_key: str, candidate_map: dict[str, dict[str, Any]]) -> str | None:
    entry = candidate_map.get(norm_key)
    if not entry:
        return None
    evidence = entry.get("evidence")
    if isinstance(evidence, str) and evidence.strip():
        return evidence.strip()
    name = entry.get("name")
    return name if name else None


def compute_match(
    profile: dict[str, Any],
    required_skills: list[RequiredSkill],
) -> JDMatchResult:
    """Pure function: score a candidate profile against required skills."""
    raw_skills: list[dict[str, Any]] = profile.get("skills") or []
    ability_tags: list[str] = profile.get("ability_tags") or []

    candidate_map: dict[str, dict[str, Any]] = {norm_skill(s.get("name", "")): s for s in raw_skills if s.get("name")}
    candidate_norm: set[str] = set(candidate_map) | {norm_skill(t) for t in ability_tags}

    skill_match: list[SkillMatchItem] = []
    for req in required_skills:
        req_norm = norm_skill(req.name)
        matched, evidence = _match_one(req_norm, candidate_norm, candidate_map)
        skill_match.append(
            SkillMatchItem(
                skill=req.name,
                matched=matched,
                critical=req.critical,
                candidate_evidence=evidence,
            )
        )

    missing_skills = [item.skill for item in skill_match if not item.matched]

    critical_required = [m for m in skill_match if m.critical]
    critical_matched = [m for m in critical_required if m.matched]
    noncritical = [m for m in skill_match if not m.critical]
    noncritical_matched = [m for m in noncritical if m.matched]

    if not skill_match:
        match_score = 0.0
    else:
        critical_ratio = len(critical_matched) / len(critical_required) if critical_required else 1.0
        noncritical_ratio = len(noncritical_matched) / len(noncritical) if noncritical else 1.0
        if critical_required and noncritical:
            match_score = round(100 * (0.7 * critical_ratio + 0.3 * noncritical_ratio), 1)
        elif critical_required:
            match_score = round(100 * critical_ratio, 1)
        elif noncritical:
            match_score = round(100 * noncritical_ratio, 1)
        else:
            match_score = 0.0

    risk: list[RiskItem] = []
    for item in skill_match:
        if not item.matched and item.critical:
            risk.append(RiskItem(level="high", message=f"缺少关键技能：{item.skill}"))
        elif not item.matched:
            risk.append(RiskItem(level="medium", message=f"缺少加分技能：{item.skill}"))

    gap: list[GapItem] = []
    if missing_skills:
        gap.append(
            GapItem(
                area="技能",
                description=f"缺失 {len(missing_skills)} 项技能：{', '.join(missing_skills)}",
            )
        )

    missing_critical = [m for m in skill_match if m.critical and not m.matched]
    if match_score >= 80 and not missing_critical:
        recommendation = "strong_hire"
    elif match_score >= 60 and len(missing_critical) <= 1:
        recommendation = "hire"
    elif match_score >= 40:
        recommendation = "conditional"
    else:
        recommendation = "reject"
    if any(r.level == "high" for r in risk) and recommendation in ("strong_hire", "hire"):
        recommendation = "conditional"

    detail_parts = [
        f"综合匹配分 {match_score}/100。",
        f"必备技能 {len(skill_match)} 项，命中 {sum(1 for m in skill_match if m.matched)} 项。",
    ]
    if missing_skills:
        detail_parts.append(f"缺失：{', '.join(missing_skills)}。")
    detail_parts.append(f"建议：{recommendation}。")
    detail = " ".join(detail_parts)

    return JDMatchResult(
        match_score=match_score,
        skill_match=skill_match,
        missing_skills=missing_skills,
        risk=risk,
        gap=gap,
        recommendation=recommendation,
        detail=detail,
    )


# Compatibility alias used by existing unit tests.
_compute_match = compute_match


__all__ = [
    "JDProcessingError",
    "_compute_match",
    "compute_match",
    "content_hash",
    "draft_from_extraction",
    "extraction_values",
    "merged_extraction_values",
    "norm_skill",
    "normalize_jd_text",
]
