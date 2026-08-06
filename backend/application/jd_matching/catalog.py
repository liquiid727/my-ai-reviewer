"""Build minimized evidence catalogs for hybrid JD matching."""

from __future__ import annotations

import re
from typing import Any

from backend.domain.jd.matching_v2 import SourceCatalogEntry

_IDENTITY_KEY_PARTS = (
    "name",
    "email",
    "mail",
    "phone",
    "mobile",
    "telephone",
    "address",
    "姓名",
    "邮箱",
    "电话",
    "手机",
    "地址",
)


def _identity_values(value: object, *, key_is_identity: bool = False) -> list[str]:
    if isinstance(value, dict):
        rows: list[str] = []
        for key, child in value.items():
            normalized = str(key).casefold()
            rows.extend(
                _identity_values(
                    child,
                    key_is_identity=key_is_identity or any(part in normalized for part in _IDENTITY_KEY_PARTS),
                )
            )
        return rows
    if isinstance(value, (list, tuple)):
        return [row for child in value for row in _identity_values(child, key_is_identity=key_is_identity)]
    if key_is_identity and isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _redact(text: object, identity_values: list[str]) -> str:
    output = str(text or "")
    for value in sorted(set(identity_values), key=len, reverse=True):
        output = re.sub(re.escape(value), "[redacted]", output, flags=re.IGNORECASE)
    return output.strip()


def _safe_excerpt(*values: object, identity_values: list[str]) -> str:
    for value in values:
        redacted = _redact(value, identity_values)
        if redacted:
            return redacted[:500]
    return "Evidence available"


def _value_from_item(item: object, *keys: str) -> str:
    if isinstance(item, dict):
        for key in keys:
            value = item.get(key)
            if value:
                return str(value)
    return str(item or "")


def build_match_source_catalog(jd: Any, profile: Any, facts: list[Any]) -> list[SourceCatalogEntry]:
    identity_values = _identity_values(getattr(profile, "identity", None) or {})
    entries: list[SourceCatalogEntry] = []
    for index, skill in enumerate(getattr(jd, "required_skills", None) or [], 1):
        label = _value_from_item(skill, "name")
        if label:
            entries.append(
                SourceCatalogEntry(
                    id=f"JD-SKILL-{index:03d}",
                    source="jd",
                    kind="required_skill",
                    label=label[:300],
                    excerpt=_safe_excerpt(
                        skill.get("evidence") if isinstance(skill, dict) else skill,
                        label,
                        identity_values=identity_values,
                    ),
                )
            )
    for index, responsibility in enumerate(getattr(jd, "responsibilities", None) or [], 1):
        entries.append(
            SourceCatalogEntry(
                id=f"JD-RESP-{index:03d}",
                source="jd",
                kind="responsibility",
                label=f"Responsibility {index}",
                excerpt=str(responsibility)[:500],
            )
        )
    for index, skill in enumerate(getattr(profile, "skills", None) or [], 1):
        label = _redact(_value_from_item(skill, "name"), identity_values)
        if label:
            entries.append(
                SourceCatalogEntry(
                    id=f"CAND-SKILL-{index:03d}",
                    source="candidate_profile",
                    kind="skill",
                    label=label[:300],
                    excerpt=label[:500],
                    confidence=_confidence(skill),
                )
            )
    for index, work in enumerate(getattr(profile, "work_experiences", None) or [], 1):
        label = (
            _redact(_value_from_item(work, "title", "company", "name"), identity_values) or f"Work experience {index}"
        )
        entries.append(
            SourceCatalogEntry(
                id=f"CAND-WORK-{index:03d}",
                source="candidate_profile",
                kind="work",
                label=label[:300],
                excerpt=_safe_excerpt(work, identity_values=identity_values),
            )
        )
    for index, project in enumerate(getattr(profile, "projects", None) or [], 1):
        label = _redact(_value_from_item(project, "name", "title"), identity_values) or f"Project {index}"
        entries.append(
            SourceCatalogEntry(
                id=f"CAND-PROJECT-{index:03d}",
                source="candidate_profile",
                kind="project",
                label=label[:300],
                excerpt=_safe_excerpt(project, identity_values=identity_values),
            )
        )
    for index, fact in enumerate(facts, 1):
        fact_type = (
            _value_from_item(fact, "fact_type") if isinstance(fact, dict) else getattr(fact, "fact_type", "fact")
        )
        fact_key = (
            _value_from_item(fact, "fact_key", "key") if isinstance(fact, dict) else getattr(fact, "fact_key", "")
        )
        evidence = (
            fact.get("evidence_source_text") if isinstance(fact, dict) else getattr(fact, "evidence_source_text", None)
        ) or fact_key
        entries.append(
            SourceCatalogEntry(
                id=f"CAND-FACT-{index:03d}",
                source="resume_fact",
                kind=str(fact_type or "fact")[:80],
                label=_redact(fact_key or fact_type or "Resume fact", identity_values)[:300],
                excerpt=_safe_excerpt(evidence, identity_values=identity_values),
                page=fact.get("evidence_page") if isinstance(fact, dict) else getattr(fact, "evidence_page", None),
                confidence=_confidence(fact),
            )
        )
    ids = [entry.id for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Source catalog contains duplicate evidence IDs")
    return entries


def _confidence(value: object) -> float | None:
    if isinstance(value, dict) and isinstance(value.get("confidence"), (int, float)):
        return float(value["confidence"])
    confidence = getattr(value, "confidence", None)
    return float(confidence) if isinstance(confidence, (int, float)) else None


__all__ = ["build_match_source_catalog"]
