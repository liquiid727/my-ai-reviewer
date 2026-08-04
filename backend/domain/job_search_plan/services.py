"""Plan domain services for source minimization, match freshness, and scheduling."""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from backend.application.llm_config_service import get_active_verified_config
from backend.domain.jd.matching import JDMatchingService
from backend.domain.job_search_plan.enums import PlanTaskSource, PlanTaskStatus
from backend.domain.job_search_plan.schemas import CatalogEntry, PlanGenerationOutput
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    FileModel,
    JDMatchResultModel,
    JobDescriptionModel,
    ResumeModel,
)
from backend.infrastructure.llm.gateway import LLMGateway
from backend.infrastructure.planners.llm_plan_generator import LLMPlanGenerator

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


class PlanDomainError(ValueError):
    """A known business failure carrying an API response code."""

    def __init__(self, message: str, code: int, data: Mapping[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = dict(data or {})


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
    jd: JobDescriptionModel,
    profile: CandidateProfileModel,
    match: JDMatchResultModel,
    *,
    target_date: date | None,
    weekly_hours: int | None,
    supplemental_background: str | None,
) -> list[CatalogEntry]:
    """Build a deterministic, identity-free catalog used by the LLM and snapshot."""
    entries: list[CatalogEntry] = []
    identity_values = _identity_values(profile.identity or {})
    for index, skill in enumerate(sorted(jd.required_skills or [], key=_catalog_sort_key), 1):
        label = str(skill.get("name", "JD skill")) if isinstance(skill, dict) else str(skill)
        entries.append(_entry("JD-SKILL", index, "jd", label, _value_text(skill)))
    for index, skill in enumerate(sorted(jd.preferred_skills or [], key=_catalog_sort_key), 1):
        label = str(skill.get("name", "JD preference")) if isinstance(skill, dict) else str(skill)
        entries.append(_entry("JD-PREF", index, "jd", label, _value_text(skill)))
    for index, skill in enumerate(sorted(profile.skills or [], key=_catalog_sort_key), 1):
        label = str(skill.get("name", "Profile skill")) if isinstance(skill, dict) else str(skill)
        # Profile skill names are a deliberate allowlist. Evidence can contain
        # contact details copied from a resume, so it never enters the prompt.
        safe_label = _redact_identity(label, identity_values)
        entries.append(_entry("PROFILE-SKILL", index, "profile", safe_label, safe_label))
    for index, tag in enumerate(sorted(profile.ability_tags or [], key=_catalog_sort_key), 1):
        safe_tag = _redact_identity(tag, identity_values)
        entries.append(_entry("PROFILE-TAG", index, "profile", safe_tag, safe_tag))
    for index, gap in enumerate(sorted(match.gap or [], key=_catalog_sort_key), 1):
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
    for index, missing in enumerate(sorted(match.missing_skills or [], key=_catalog_sort_key), 1):
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


async def get_eligible_resume_options(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, object]], int]:
    """Select only resume option fields; never hydrate profile identity/raw resume text."""
    statement = (
        select(ResumeModel.id, ResumeModel.updated_at, FileModel.original_name)
        .join(CandidateProfileModel, CandidateProfileModel.resume_id == ResumeModel.id)
        .outerjoin(FileModel, FileModel.id == ResumeModel.file_id)
        .order_by(ResumeModel.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(statement)).all()
    total = (
        await session.execute(
            select(func.count())
            .select_from(ResumeModel)
            .join(CandidateProfileModel, CandidateProfileModel.resume_id == ResumeModel.id)
        )
    ).scalar_one()
    return (
        [
            {
                "id": str(row.id),
                "display_name": row.original_name or f"Resume {str(row.id)[:8]}",
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ],
        int(total),
    )


async def get_fresh_match(
    session: AsyncSession,
    *,
    jd: JobDescriptionModel,
    resume_id: uuid.UUID,
) -> tuple[CandidateProfileModel, JDMatchResultModel]:
    """Reuse a match only when it is at least as new as both upstream documents."""
    profile = (
        await session.execute(
            select(CandidateProfileModel)
            .where(CandidateProfileModel.resume_id == resume_id)
            .options(noload(CandidateProfileModel.resume))
        )
    ).scalar_one_or_none()
    if profile is None:
        raise PlanDomainError("Resume does not have a candidate profile", 1008)
    latest = (
        await session.execute(
            select(JDMatchResultModel)
            .where(JDMatchResultModel.jd_id == jd.id, JDMatchResultModel.resume_id == resume_id)
            .order_by(JDMatchResultModel.created_at.desc())
            .limit(1)
            .options(noload(JDMatchResultModel.resume), noload(JDMatchResultModel.jd))
        )
    ).scalar_one_or_none()
    upstream_dates = [value for value in (jd.updated_at, profile.updated_at) if value is not None]
    stale = latest is None or any(latest.created_at < updated_at for updated_at in upstream_dates)
    if stale:
        latest = await JDMatchingService().match(session, resume_id, jd)
        await session.flush()
    assert latest is not None
    return profile, latest


async def generate_plan_output(
    session: AsyncSession,
    catalog: list[CatalogEntry],
    *,
    target_date: date,
    weekly_hours: int | None,
) -> tuple[PlanGenerationOutput, str]:
    """Use only the active verified database configuration for plan generation."""
    config = await get_active_verified_config(session)
    if config is None:
        await session.rollback()
        raise PlanDomainError("LLM not configured or not verified", 428)
    generator = LLMPlanGenerator(LLMGateway.from_config(config))
    # The gateway owns the decrypted configuration now. Release the database
    # transaction before the provider call, which can take the full task timeout.
    await session.rollback()
    output = await generator.generate(
        catalog,
        target_date=target_date.isoformat(),
        weekly_hours=weekly_hours or 8,
    )
    return output, generator.model_info


def generation_today() -> date:
    """Make schedule semantics explicit and testable in the application timezone."""
    from datetime import datetime

    return datetime.now(SHANGHAI_TZ).date()
