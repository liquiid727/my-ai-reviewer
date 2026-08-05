"""Source Catalog normalization (RIP-013 §6.2).

Builds the typed, stable evidence catalog that the constrained semantic
classifier may cite. Only catalog IDs are valid citations; the builder never
emits unmasked content — `masked_excerpt` carries the version's masked text
or a normalized claim, never raw identifiers.
"""

from __future__ import annotations

from typing import Any

from backend.domain.match_assessment.policy import normalize_skill
from backend.domain.match_assessment.schemas import SourceCatalog, SourceCatalogItem

_JD_PREFIX = "jd"
_RESUME_PREFIX = "resume"

# Scalar candidate profile fields that may become normalized claims.
_PROFILE_CLAIMS: dict[str, str] = {
    "title": "job title",
    "summary": "summary",
    "location": "location",
}


def _masked_excerpt(excerpt: str | None) -> str | None:
    if not excerpt:
        return None
    stripped = excerpt.strip()
    return stripped if stripped else None


def _jd_items(
    jd_version_id: str,
    structured: dict[str, Any],
) -> list[SourceCatalogItem]:
    items: list[SourceCatalogItem] = []
    prefix = f"{_JD_PREFIX}:{jd_version_id}"

    requirements = structured.get("required_skills") or []
    for index, item in enumerate(requirements):
        if not isinstance(item, dict):
            continue
        key = item.get("key") or f"req-{index}"
        value = item.get("value")
        if not value:
            continue
        items.append(
            SourceCatalogItem(
                id=f"{prefix}:requirement:{key}",
                kind="requirement",
                claim=str(value),
                masked_excerpt=_masked_excerpt(item.get("evidence")),
                provenance="source",
                confidence=float(item.get("confidence") or 0.0),
            )
        )

    responsibilities = structured.get("responsibilities") or []
    for index, item in enumerate(responsibilities):
        if not isinstance(item, dict):
            continue
        key = item.get("key") or f"res-{index}"
        value = item.get("value")
        if not value:
            continue
        items.append(
            SourceCatalogItem(
                id=f"{prefix}:responsibility:{key}",
                kind="responsibility",
                claim=str(value),
                masked_excerpt=_masked_excerpt(item.get("evidence")),
                provenance="source",
                confidence=float(item.get("confidence") or 0.0),
            )
        )
    return items


def _resume_items(
    resume_version_id: str,
    profile: dict[str, Any],
    facts: list[Any],
) -> list[SourceCatalogItem]:
    items: list[SourceCatalogItem] = []
    prefix = f"{_RESUME_PREFIX}:{resume_version_id}"

    for index, fact in enumerate(facts):
        if not isinstance(fact, dict):
            continue
        key = fact.get("key") or f"fact-{index}"
        value = fact.get("value")
        evidence = fact.get("evidence")
        if isinstance(evidence, dict):
            excerpt = evidence.get("source_text")
        else:
            excerpt = None
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            import json

            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
        items.append(
            SourceCatalogItem(
                id=f"{prefix}:fact:{key}",
                kind="fact",
                claim=str(value),
                masked_excerpt=_masked_excerpt(str(excerpt)) if excerpt is not None else None,
                provenance="source",
                confidence=0.0,
            )
        )

    skills = profile.get("skills") or []
    for index, skill in enumerate(skills):
        if not isinstance(skill, dict):
            continue
        name = skill.get("name")
        if not name:
            continue
        items.append(
            SourceCatalogItem(
                id=f"{prefix}:fact:skill-{index}",
                kind="fact",
                claim=normalize_skill(str(name)),
                masked_excerpt=_masked_excerpt(skill.get("evidence")),
                provenance="source",
                confidence=float(skill.get("confidence") or 0.0),
            )
        )

    projects = profile.get("projects") or []
    for index, project in enumerate(projects):
        if not isinstance(project, dict):
            continue
        name = project.get("name") or f"project-{index}"
        items.append(
            SourceCatalogItem(
                id=f"{prefix}:project:{index}",
                kind="project",
                claim=str(name),
                masked_excerpt=_masked_excerpt(
                    " ".join(
                        str(part)
                        for part in (project.get("background"), project.get("responsibility"))
                        if part
                    )
                    or None
                ),
                provenance="source",
                confidence=0.0,
            )
        )

    for field, label in _PROFILE_CLAIMS.items():
        value = profile.get(field)
        if value:
            items.append(
                SourceCatalogItem(
                    id=f"{prefix}:profile:{field}",
                    kind="profile",
                    claim=f"{label}: {value}",
                    masked_excerpt=None,
                    provenance="source",
                    confidence=0.0,
                )
            )
    return items


def build_catalog(
    *,
    jd_version_id: str,
    jd_structured: dict[str, Any],
    resume_version_id: str,
    resume_profile: dict[str, Any],
    resume_facts: list[Any],
) -> SourceCatalog:
    """Normalize both versions into one typed, citeable evidence catalog."""
    return SourceCatalog(
        items=[
            *_jd_items(jd_version_id, jd_structured),
            *_resume_items(resume_version_id, resume_profile, resume_facts),
        ]
    )
