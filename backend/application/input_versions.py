"""Input version application use cases (RIP-010 §7.1, §7.2)."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.privacy import PrivacyGuard
from backend.domain.privacy.redactor import PrivacyViolationError
from backend.infrastructure.db.models import (
    JobDescriptionVersionModel,
    ResumeDraftModel,
    ResumeModel,
    ResumeVersionModel,
)


class InputVersionError(Exception):
    """Base input-version error."""


class SourceNotReadyError(InputVersionError):
    """Resume/profile/draft is not publishable."""


class SourceRevisionChangedError(InputVersionError):
    """Builder/source revision changed during publication."""


class PrivacyRejectedError(InputVersionError):
    """Snapshot fails PrivacyGuard."""


class VersionNotFoundError(InputVersionError):
    """Requested version does not exist."""


@dataclass(frozen=True)
class PublishResumeVersionCommand:
    source_type: str
    resume_id: uuid.UUID | None = None
    draft_id: uuid.UUID | None = None
    source_revision: int | None = None


@dataclass(frozen=True)
class ResumeVersionResult:
    id: uuid.UUID
    source_type: str
    resume_id: uuid.UUID | None
    draft_id: uuid.UUID | None
    source_revision: int
    content_hash: str
    schema_version: str
    privacy_policy_version: str
    published_at: datetime
    created: bool


def _hash(payload: dict[str, Any]) -> str:
    import json

    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _parse_resume_snapshot(resume: ResumeModel) -> dict[str, Any]:
    """Build a masked snapshot from an evaluated resume."""
    masked = resume.masked_text or ""
    parsed = resume.parsed_result or {}
    profile = parsed.get("profile", {})
    facts = parsed.get("facts", parsed.get("resume_facts", []))
    return {
        "masked_text": masked,
        "profile": profile,
        "facts": facts,
        "classification": parsed.get("classification", {}),
    }


def _builder_snapshot(draft: ResumeDraftModel) -> dict[str, Any]:
    """Build a masked snapshot from a saved builder draft revision."""
    return {
        "draft": draft.content or {},
        "privacy_manifest": draft.privacy_manifest or {},
    }


class ResumeVersionUseCases:
    """Publish-or-resolve immutable Resume Versions."""

    async def publish_or_resolve(
        self,
        session: AsyncSession,
        command: PublishResumeVersionCommand,
    ) -> ResumeVersionResult:
        if command.source_type == "parsed_resume":
            return await self._publish_parsed(session, command)
        if command.source_type == "builder_draft":
            return await self._publish_builder(session, command)
        raise SourceNotReadyError(f"unknown source_type {command.source_type}")

    async def _publish_parsed(
        self,
        session: AsyncSession,
        command: PublishResumeVersionCommand,
    ) -> ResumeVersionResult:
        if command.resume_id is None:
            raise SourceNotReadyError("resume_id is required for parsed_resume")
        resume = await session.get(ResumeModel, command.resume_id)
        if resume is None:
            raise SourceNotReadyError("resume not found")
        if resume.status != "evaluated":
            raise SourceNotReadyError("resume is not evaluated")

        snapshot = _parse_resume_snapshot(resume)
        content_hash = _hash(snapshot)
        parser_version = resume.parser_version or "legacy"
        schema_version = "resume-v1"
        privacy_policy_version = "resume-privacy-v1"
        source_revision = 1  # parsed resume has no revision counter

        existing = await self._find_existing(
            session,
            resume_id=command.resume_id,
            content_hash=content_hash,
            schema_version=schema_version,
        )
        if existing is not None:
            return self._to_result(existing, created=False)

        try:
            PrivacyGuard().assert_masked(snapshot)
        except PrivacyViolationError as exc:
            raise PrivacyRejectedError(str(exc)) from exc

        version = ResumeVersionModel(
            id=uuid.uuid4(),
            source_type="parsed_resume",
            resume_id=command.resume_id,
            draft_id=None,
            source_revision=source_revision,
            content_hash=content_hash,
            masked_snapshot=snapshot,
            profile_snapshot=snapshot.get("profile", {}),
            evidence_catalog=[],
            parser_version=parser_version,
            schema_version=schema_version,
            privacy_policy_version=privacy_policy_version,
        )
        session.add(version)
        await session.commit()
        await session.refresh(version)
        return self._to_result(version, created=True)

    async def _publish_builder(
        self,
        session: AsyncSession,
        command: PublishResumeVersionCommand,
    ) -> ResumeVersionResult:
        if command.draft_id is None:
            raise SourceNotReadyError("draft_id is required for builder_draft")
        draft = await session.get(ResumeDraftModel, command.draft_id)
        if draft is None:
            raise SourceNotReadyError("draft not found")
        if command.source_revision is not None and draft.revision != command.source_revision:
            raise SourceRevisionChangedError(
                f"draft revision {draft.revision} does not match expected {command.source_revision}"
            )

        snapshot = _builder_snapshot(draft)
        content_hash = _hash(snapshot)
        parser_version = "builder-v1"
        schema_version = "builder-resume-v1"
        privacy_policy_version = "resume-privacy-v1"
        source_revision = draft.revision

        existing = await self._find_existing(
            session,
            draft_id=command.draft_id,
            source_revision=source_revision,
            content_hash=content_hash,
            schema_version=schema_version,
        )
        if existing is not None:
            return self._to_result(existing, created=False)

        try:
            PrivacyGuard().assert_masked(snapshot)
        except PrivacyViolationError as exc:
            raise PrivacyRejectedError(str(exc)) from exc

        version = ResumeVersionModel(
            id=uuid.uuid4(),
            source_type="builder_draft",
            resume_id=draft.resume_id,
            draft_id=command.draft_id,
            source_revision=source_revision,
            content_hash=content_hash,
            masked_snapshot=snapshot,
            profile_snapshot={},
            evidence_catalog=[],
            parser_version=parser_version,
            schema_version=schema_version,
            privacy_policy_version=privacy_policy_version,
        )
        session.add(version)
        await session.commit()
        await session.refresh(version)
        return self._to_result(version, created=True)

    async def _find_existing(
        self,
        session: AsyncSession,
        *,
        resume_id: uuid.UUID | None = None,
        draft_id: uuid.UUID | None = None,
        source_revision: int | None = None,
        content_hash: str,
        schema_version: str,
    ) -> ResumeVersionModel | None:
        stmt = select(ResumeVersionModel).where(
            ResumeVersionModel.content_hash == content_hash,
            ResumeVersionModel.schema_version == schema_version,
        )
        if resume_id is not None:
            stmt = stmt.where(ResumeVersionModel.resume_id == resume_id)
        if draft_id is not None:
            stmt = stmt.where(ResumeVersionModel.draft_id == draft_id)
            stmt = stmt.where(ResumeVersionModel.source_revision == source_revision)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _to_result(version: ResumeVersionModel, *, created: bool) -> ResumeVersionResult:
        return ResumeVersionResult(
            id=version.id,
            source_type=version.source_type,
            resume_id=version.resume_id,
            draft_id=version.draft_id,
            source_revision=version.source_revision,
            content_hash=version.content_hash,
            schema_version=version.schema_version,
            privacy_policy_version=version.privacy_policy_version,
            published_at=version.published_at,
            created=created,
        )


class ResumeVersionQueries:
    """Read-only Resume Version queries."""

    async def list(
        self,
        session: AsyncSession,
        *,
        resume_id: uuid.UUID | None = None,
        draft_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[ResumeVersionModel]:
        stmt = (
            select(ResumeVersionModel)
            .order_by(ResumeVersionModel.published_at.desc())
            .limit(limit)
        )
        if resume_id is not None:
            stmt = stmt.where(ResumeVersionModel.resume_id == resume_id)
        if draft_id is not None:
            stmt = stmt.where(ResumeVersionModel.draft_id == draft_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get(
        self,
        session: AsyncSession,
        version_id: uuid.UUID,
    ) -> ResumeVersionModel | None:
        return await session.get(ResumeVersionModel, version_id)


class JDVersionQueries:
    """Read-only JD Version queries (list/detail)."""

    async def list_for_jd(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
        *,
        limit: int = 50,
        cursor_updated_at: datetime | None = None,
        cursor_id: uuid.UUID | None = None,
    ) -> list[JobDescriptionVersionModel]:
        stmt = (
            select(JobDescriptionVersionModel)
            .where(JobDescriptionVersionModel.job_description_id == jd_id)
            .order_by(
                JobDescriptionVersionModel.published_at.desc(),
                JobDescriptionVersionModel.id.desc(),
            )
            .limit(limit)
        )
        if cursor_updated_at is not None and cursor_id is not None:
            stmt = stmt.where(
                (JobDescriptionVersionModel.published_at < cursor_updated_at)
                | (
                    (JobDescriptionVersionModel.published_at == cursor_updated_at)
                    & (JobDescriptionVersionModel.id < cursor_id)
                )
            )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get(
        self,
        session: AsyncSession,
        version_id: uuid.UUID,
    ) -> JobDescriptionVersionModel | None:
        return await session.get(JobDescriptionVersionModel, version_id)
