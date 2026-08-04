"""Pure plan domain policies (no I/O, ORM, or infrastructure)."""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from backend.domain.job_search_plan.enums import PlanTaskSource, PlanTaskStatus
from backend.domain.job_search_plan.schemas import CatalogEntry, PlanGenerationOutput

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")

_IDENTITY_KEY_PARTS = (
    "name",
    "email",
    "mail",
    "phone",
    "mobile",
    "telephone",
    "tel",
    "address",
    "姓名",
    "邮箱",
    "邮件",
    "电话",
    "手机",
    "地址",
)


class PlanDomainError(ValueError):
    """A known business failure carrying an API response code."""

    def __init__(self, message: str, code: int, data: Mapping[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = dict(data or {})


def generation_today() -> date:
    """Make schedule semantics explicit and testable in the application timezone."""
    return datetime.now(SHANGHAI_TZ).date()


def _entry(prefix: str, index: int, source: str, label: str, excerpt: str) -> CatalogEntry:
    return CatalogEntry(
        id=f"{prefix}-{index:03d}",
        source=source,  # type: ignore[arg-type]
        label=label.strip()[:300] or prefix,
        excerpt=excerpt.strip()[:500] or label.strip()[:300] or prefix,
    )


def _value_text(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("evidence") or value.get("name") or value.get("description") or "")
    return str(value)


def _catalog_sort_key(value: object) -> tuple[str, str]:
    if isinstance(value, dict):
        label = str(value.get("name") or value.get("area") or value.get("label") or "")
    else:
        label = str(value)
    return (label.casefold(), _value_text(value).casefold())


def _identity_values(value: object, *, key_is_identity: bool = False) -> list[str]:
    """Collect only identity-field values so profile evidence can be redacted."""
    if isinstance(value, dict):
        values: list[str] = []
        for key, child in value.items():
            normalized_key = str(key).casefold()
            values.extend(
                _identity_values(
                    child,
                    key_is_identity=any(part in normalized_key for part in _IDENTITY_KEY_PARTS),
                )
            )
        return values
    if isinstance(value, (list, tuple)):
        return [item for child in value for item in _identity_values(child, key_is_identity=key_is_identity)]
    if key_is_identity and isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _redact_identity(text: object, identity_values: list[str]) -> str:
    redacted = str(text)
    for value in sorted(set(identity_values), key=len, reverse=True):
        redacted = re.sub(re.escape(value), "[redacted]", redacted, flags=re.IGNORECASE)
    return redacted


def build_source_catalog(
    jd: Any,
    profile: Any,
    match: Any,
    *,
    target_date: date | None,
    weekly_hours: int | None,
    supplemental_background: str | None,
) -> list[CatalogEntry]:
    """Build a deterministic, identity-free catalog used by the LLM and snapshot.

    Accepts duck-typed JD / profile / match objects (ORM models or plain namespaces).
    """
    entries: list[CatalogEntry] = []
    identity_values = _identity_values(getattr(profile, "identity", None) or {})
    for index, skill in enumerate(sorted(getattr(jd, "required_skills", None) or [], key=_catalog_sort_key), 1):
        label = str(skill.get("name", "JD skill")) if isinstance(skill, dict) else str(skill)
        entries.append(_entry("JD-SKILL", index, "jd", label, _value_text(skill)))
    for index, skill in enumerate(sorted(getattr(jd, "preferred_skills", None) or [], key=_catalog_sort_key), 1):
        label = str(skill.get("name", "JD preference")) if isinstance(skill, dict) else str(skill)
        entries.append(_entry("JD-PREF", index, "jd", label, _value_text(skill)))
    for index, skill in enumerate(sorted(getattr(profile, "skills", None) or [], key=_catalog_sort_key), 1):
        label = str(skill.get("name", "Profile skill")) if isinstance(skill, dict) else str(skill)
        # Profile skill names are a deliberate allowlist. Evidence can contain
        # contact details copied from a resume, so it never enters the prompt.
        safe_label = _redact_identity(label, identity_values)
        entries.append(_entry("PROFILE-SKILL", index, "profile", safe_label, safe_label))
    for index, tag in enumerate(sorted(getattr(profile, "ability_tags", None) or [], key=_catalog_sort_key), 1):
        safe_tag = _redact_identity(tag, identity_values)
        entries.append(_entry("PROFILE-TAG", index, "profile", safe_tag, safe_tag))
    for index, gap in enumerate(sorted(getattr(match, "gap", None) or [], key=_catalog_sort_key), 1):
        label = str(gap.get("area", "Match gap")) if isinstance(gap, dict) else "Match gap"
        entries.append(
            _entry(
                "MATCH-GAP",
                index,
                "match",
                _redact_identity(label, identity_values),
                _redact_identity(_value_text(gap), identity_values),
            )
        )
    for index, missing in enumerate(sorted(getattr(match, "missing_skills", None) or [], key=_catalog_sort_key), 1):
        safe_missing = _redact_identity(missing, identity_values)
        entries.append(_entry("MATCH-MISSING", index, "match", safe_missing, f"Missing skill: {safe_missing}"))

    preferences: list[tuple[str, str]] = [("Target date", target_date.isoformat() if target_date else "28-day horizon")]
    preferences.append(("Weekly available hours", str(weekly_hours or 8)))
    if supplemental_background and supplemental_background.strip():
        preferences.append(("Supplemental background", supplemental_background.strip()))
    for index, (label, excerpt) in enumerate(preferences, 1):
        entries.append(_entry("PREF", index, "preference", label, excerpt))

    ids = [entry.id for entry in entries]
    if len(ids) != len(set(ids)):
        raise PlanDomainError("Source catalog contains duplicate IDs", 5006)
    return entries


def resolve_basis(catalog: list[CatalogEntry], basis_ids: list[str]) -> list[dict[str, str]]:
    by_id = {entry.id: entry for entry in catalog}
    if len(by_id) != len(catalog) or len(set(basis_ids)) != len(basis_ids):
        raise PlanDomainError("Source evidence is invalid", 5006)
    try:
        return [by_id[basis_id].model_dump() for basis_id in basis_ids]
    except KeyError as exc:
        raise PlanDomainError("Plan referenced unknown source evidence", 5006) from exc


def normalize_generated_tasks(
    output: PlanGenerationOutput,
    catalog: list[CatalogEntry],
    *,
    target_date: date | None,
    today: date | None = None,
) -> list[dict[str, object]]:
    """Resolve catalog evidence and clamp relative due dates server-side."""
    start = today or generation_today()
    horizon = target_date or start + timedelta(days=28)
    normalized: list[dict[str, object]] = []
    for sort_order, task in enumerate(output.tasks):
        due_date = min(start + timedelta(days=task.due_offset_days), horizon)
        normalized.append(
            {
                "title": task.title.strip(),
                "category": task.category.value,
                "description": task.description.strip(),
                "basis": resolve_basis(catalog, task.basis_ids),
                "source": PlanTaskSource.AI.value,
                "priority": task.priority.value,
                "status": PlanTaskStatus.TODO.value,
                "due_date": due_date,
                "sort_order": sort_order,
            }
        )
    return normalized


def sanitized_input_snapshot(
    catalog: list[CatalogEntry],
    *,
    match_id: uuid.UUID | None,
    target_date: date | None,
    weekly_hours: int | None,
    supplemental_background: str | None,
    model_name: str,
) -> dict[str, object]:
    """Persist only the already minimized catalog, never CandidateProfile.identity."""
    return {
        "catalog": [entry.model_dump() for entry in catalog],
        "match_result_id": str(match_id) if match_id else None,
        "model": model_name,
        "preferences": {
            "target_date": target_date.isoformat() if target_date else None,
            "weekly_hours": weekly_hours,
            "supplemental_background": supplemental_background or None,
        },
    }
