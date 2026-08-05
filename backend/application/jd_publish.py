"""JD version publication use cases (RIP-011 §6.2, §7.1, §9.2)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.jd.enums import JDProcessingStep, JDStatus
from backend.infrastructure.db.models import (
    JobDescriptionModel,
    JobDescriptionVersionModel,
)


class JDPublishError(Exception):
    """Base JD publish error."""


class JDPublishInvalidError(JDPublishError):
    """Review draft is not complete/valid for publication."""


class JDPublishConflictError(JDPublishError):
    """Expected review revision is stale or JD not in review."""


class JDVersionNotFoundError(JDPublishError):
    """Requested version does not exist."""


@dataclass(frozen=True)
class PublishJDCommand:
    jd_id: uuid.UUID
    expected_review_revision: int
    publication_reason: str = "user_confirmed"


class JDPublishUseCases:
    """Idempotent publication of immutable JD versions from the review draft."""

    async def publish(
        self,
        session: AsyncSession,
        command: PublishJDCommand,
    ) -> JobDescriptionVersionModel:
        jd = await session.get(JobDescriptionModel, command.jd_id)
        if jd is None:
            raise JDPublishInvalidError("JD not found")
        if jd.review_revision != command.expected_review_revision:
            raise JDPublishConflictError(
                f"expected review revision {command.expected_review_revision}, "
                f"current {jd.review_revision}"
            )
        if not jd.review_draft:
            raise JDPublishConflictError("JD has no review draft to publish")
        if not jd.review_draft.get("title"):
            raise JDPublishInvalidError("review draft requires a title")

        snapshot = self._canonical_snapshot(jd)
        content_hash = self._hash(snapshot)
        schema_version = "jd-review-v1"

        # Idempotent: same (jd, content_hash, schema_version) resolves to existing,
        # even after the JD has already transitioned to ready.
        existing = await self._find_existing(session, jd.id, content_hash, schema_version)
        if existing is not None:
            return existing

        if jd.status != JDStatus.NEEDS_REVIEW.value:
            raise JDPublishConflictError(
                f"JD status {jd.status} is not reviewable for a new publication"
            )

        parser_version = jd.review_draft.get("parser_version") or jd.parser_version or "legacy"
        model_name = jd.review_draft.get("model_name")

        version = JobDescriptionVersionModel(
            id=uuid.uuid4(),
            job_description_id=jd.id,
            version_no=await self._next_version_no(session, jd.id),
            normalized_text=jd.raw_text.strip(),
            structured=snapshot.get("structured", {}),
            evidence=snapshot.get("evidence", {}),
            source_metadata=snapshot.get("source_metadata", {}),
            content_hash=content_hash,
            parser_version=parser_version,
            model_name=model_name,
            schema_version=schema_version,
            publication_reason=command.publication_reason,
        )
        session.add(version)
        # Persist the version row before the JD's FK references it.
        await session.flush()
        jd.current_version_id = version.id
        jd.status = JDStatus.READY.value
        jd.processing_step = JDProcessingStep.DONE.value
        await session.commit()
        await session.refresh(version)
        return version

    async def get(
        self,
        session: AsyncSession,
        version_id: uuid.UUID,
    ) -> JobDescriptionVersionModel | None:
        return await session.get(JobDescriptionVersionModel, version_id)

    async def list_for_jd(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[JobDescriptionVersionModel]:
        stmt = (
            select(JobDescriptionVersionModel)
            .where(JobDescriptionVersionModel.job_description_id == jd_id)
            .order_by(JobDescriptionVersionModel.version_no.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _canonical_snapshot(jd: JobDescriptionModel) -> dict[str, Any]:
        draft = jd.review_draft or {}
        structured = {
            "title": draft.get("title"),
            "company": draft.get("company"),
            "department": draft.get("department"),
            "location": draft.get("location"),
            "employment_type": draft.get("employment_type"),
            "seniority": draft.get("seniority"),
            "compensation": draft.get("compensation"),
            "minimum_years": draft.get("minimum_years"),
            "preferred_years": draft.get("preferred_years"),
            "education": draft.get("education"),
            "languages": draft.get("languages") or [],
            "certificates": draft.get("certificates") or [],
            "location_constraint": draft.get("location_constraint"),
            "responsibilities": draft.get("responsibilities") or [],
            "required_skills": draft.get("required_skills") or [],
            "preferred_skills": draft.get("preferred_skills") or [],
            "hard_conditions": draft.get("hard_conditions") or [],
            "domain_context": draft.get("domain_context"),
            "industry_context": draft.get("industry_context"),
            "interview_clues": draft.get("interview_clues") or [],
            "notes": draft.get("notes"),
        }
        return {
            "structured": structured,
            "evidence": {
                "items": [
                    item
                    for kind in ("responsibilities", "required_skills", "preferred_skills", "hard_conditions")
                    for item in (draft.get(kind) or [])
                    if item.get("evidence")
                ]
            },
            "source_metadata": {
                "source_type": jd.source_type,
                "source_url": jd.source_url,
                "source_file_id": str(jd.source_file_id) if jd.source_file_id else None,
                "generator": {
                    "parser_version": draft.get("parser_version"),
                    "model_name": draft.get("model_name"),
                    "prompt_version": draft.get("prompt_version"),
                    "schema_version": draft.get("schema_version"),
                },
            },
        }

    @staticmethod
    def _hash(snapshot: dict[str, Any]) -> str:
        return hashlib.sha256(
            json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    @staticmethod
    async def _find_existing(
        session: AsyncSession,
        jd_id: uuid.UUID,
        content_hash: str,
        schema_version: str,
    ) -> JobDescriptionVersionModel | None:
        stmt = select(JobDescriptionVersionModel).where(
            JobDescriptionVersionModel.job_description_id == jd_id,
            JobDescriptionVersionModel.content_hash == content_hash,
            JobDescriptionVersionModel.schema_version == schema_version,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def _next_version_no(
        session: AsyncSession,
        jd_id: uuid.UUID,
    ) -> int:
        stmt = select(JobDescriptionVersionModel.version_no).where(
            JobDescriptionVersionModel.job_description_id == jd_id
        )
        result = await session.execute(stmt)
        existing = [r for r in result.scalars().all()]
        return max(existing) + 1 if existing else 1
