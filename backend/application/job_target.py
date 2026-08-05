"""Job Target application use cases (RIP-010 §7.1, §7.3, §9.3)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.job_target.policies import (
    DefaultUpdate,
    JobTargetPolicy,
    JobTargetState,
)
from backend.domain.job_target.policies import (
    JobTargetArchivedError as PolicyArchivedError,
)
from backend.domain.job_target.policies import (
    JobTargetRevisionConflictError as PolicyRevisionConflictError,
)
from backend.domain.job_target.policies import (
    VersionScopeMismatchError as PolicyScopeMismatchError,
)
from backend.infrastructure.db.models import (
    JobDescriptionModel,
    JobDescriptionVersionModel,
    JobTargetModel,
    ResumeVersionModel,
)


class JobTargetUseCaseError(Exception):
    """Base Job Target application error."""


class JobTargetNotFoundError(JobTargetUseCaseError):
    """Requested target does not exist."""


class JobTargetArchivedError(JobTargetUseCaseError, PolicyArchivedError):
    """Mutation targeted an archived workspace."""


class JobTargetRevisionConflictError(JobTargetUseCaseError, PolicyRevisionConflictError):
    """Expected revision is stale."""


class VersionScopeMismatchError(JobTargetUseCaseError, PolicyScopeMismatchError):
    """Default version does not belong to the selected identity."""


class JobDescriptionNotFoundError(JobTargetUseCaseError):
    """Referenced JD identity does not exist."""


@dataclass(frozen=True)
class EnsureTargetCommand:
    jd_id: uuid.UUID
    default_jd_version_id: uuid.UUID | None = None
    default_resume_version_id: uuid.UUID | None = None


@dataclass(frozen=True)
class UpdateDefaultsCommand:
    target_id: uuid.UUID
    expected_revision: int
    default_jd_version_id: uuid.UUID | None = None
    default_resume_version_id: uuid.UUID | None = None


@dataclass(frozen=True)
class ArchiveTargetCommand:
    target_id: uuid.UUID
    expected_revision: int


@dataclass(frozen=True)
class TargetResult:
    id: uuid.UUID
    job_description_id: uuid.UUID
    default_jd_version_id: uuid.UUID | None
    default_resume_version_id: uuid.UUID | None
    revision: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    created: bool = False
    # Enrichment for the target detail UI (RIP-014 §7.1): the owning JD and
    # the pinned version identities, resolved once per read.
    job: JobSummary | None = None
    current_jd_version: JdVersionSummary | None = None
    default_resume_version: ResumeVersionSummary | None = None


@dataclass(frozen=True)
class JobSummary:
    id: uuid.UUID
    title: str | None
    company: str | None


@dataclass(frozen=True)
class JdVersionSummary:
    id: uuid.UUID
    version_no: int
    published_at: datetime | None


@dataclass(frozen=True)
class ResumeVersionSummary:
    id: uuid.UUID
    source_type: str
    published_at: datetime | None


def _to_result(
    target: JobTargetModel,
    *,
    created: bool = False,
    job: JobSummary | None = None,
    current_jd_version: JdVersionSummary | None = None,
    default_resume_version: ResumeVersionSummary | None = None,
) -> TargetResult:
    return TargetResult(
        id=target.id,
        job_description_id=target.job_description_id,
        default_jd_version_id=target.default_jd_version_id,
        default_resume_version_id=target.default_resume_version_id,
        revision=target.revision,
        created_at=target.created_at,
        updated_at=target.updated_at,
        archived_at=target.archived_at,
        created=created,
        job=job,
        current_jd_version=current_jd_version,
        default_resume_version=default_resume_version,
    )


class JobTargetUseCases:
    """Idempotent Job Target commands with revision-safe defaults and archive."""

    def __init__(self) -> None:
        self._policy = JobTargetPolicy()

    async def ensure(
        self,
        session: AsyncSession,
        command: EnsureTargetCommand,
    ) -> TargetResult:
        """Return the active target for a JD, creating it if needed (idempotent)."""
        await self._validate_versions(
            session,
            command.jd_id,
            command.default_jd_version_id,
            command.default_resume_version_id,
        )

        existing = await self._active_for_jd(session, command.jd_id)
        if existing is not None:
            return await self._enrich(session, existing)

        target = JobTargetModel(
            id=uuid.uuid4(),
            job_description_id=command.jd_id,
            default_jd_version_id=command.default_jd_version_id,
            default_resume_version_id=command.default_resume_version_id,
            revision=1,
        )
        session.add(target)
        try:
            await session.commit()
        except IntegrityError:
            # Concurrent insert lost the partial-unique race; reload the winner.
            await session.rollback()
            winner = await self._active_for_jd(session, command.jd_id)
            if winner is None:
                raise
            return await self._enrich(session, winner)
        await session.refresh(target)
        return await self._enrich(session, target, created=True)

    async def get(
        self,
        session: AsyncSession,
        target_id: uuid.UUID,
    ) -> TargetResult:
        target = await session.get(JobTargetModel, target_id)
        if target is None:
            raise JobTargetNotFoundError(f"job target {target_id} not found")
        return await self._enrich(session, target)

    async def list_active(
        self,
        session: AsyncSession,
        *,
        limit: int = 100,
        include_archived: bool = False,
    ) -> list[TargetResult]:
        stmt = select(JobTargetModel).order_by(JobTargetModel.updated_at.desc()).limit(limit)
        if not include_archived:
            stmt = stmt.where(JobTargetModel.archived_at.is_(None))
        result = await session.execute(stmt)
        return [_to_result(t) for t in result.scalars().all()]

    async def update_defaults(
        self,
        session: AsyncSession,
        command: UpdateDefaultsCommand,
    ) -> TargetResult:
        target = await session.get(JobTargetModel, command.target_id)
        if target is None:
            raise JobTargetNotFoundError(f"job target {command.target_id} not found")

        await self._validate_versions(
            session,
            target.job_description_id,
            command.default_jd_version_id,
            command.default_resume_version_id,
        )
        state = self._state(target)
        try:
            self._policy.validate_default_update(
                state,
                DefaultUpdate(
                    command.default_jd_version_id,
                    command.default_resume_version_id,
                ),
                command.expected_revision,
                jd_version_owner=await self._jd_version_owner(session, command.default_jd_version_id),
                resume_version_owner=await self._resume_version_owner(session, command.default_resume_version_id),
            )
        except PolicyArchivedError as exc:
            raise JobTargetArchivedError(str(exc)) from exc
        except PolicyRevisionConflictError as exc:
            raise JobTargetRevisionConflictError(str(exc)) from exc
        except PolicyScopeMismatchError as exc:
            raise VersionScopeMismatchError(str(exc)) from exc

        target.default_jd_version_id = command.default_jd_version_id
        target.default_resume_version_id = command.default_resume_version_id
        target.revision = self._policy.next_revision(state)
        await session.commit()
        await session.refresh(target)
        return await self._enrich(session, target)

    async def archive(
        self,
        session: AsyncSession,
        command: ArchiveTargetCommand,
    ) -> TargetResult:
        target = await session.get(JobTargetModel, command.target_id)
        if target is None:
            raise JobTargetNotFoundError(f"job target {command.target_id} not found")
        state = self._state(target)
        try:
            self._policy.validate_archive(state, command.expected_revision)
        except PolicyArchivedError as exc:
            raise JobTargetArchivedError(str(exc)) from exc
        except PolicyRevisionConflictError as exc:
            raise JobTargetRevisionConflictError(str(exc)) from exc

        target.archived_at = datetime.now(timezone.utc)
        target.revision = self._policy.next_revision(state)
        await session.commit()
        await session.refresh(target)
        return await self._enrich(session, target)

    async def _enrich(
        self,
        session: AsyncSession,
        target: JobTargetModel,
        *,
        created: bool = False,
    ) -> TargetResult:
        """Resolve the owning JD and pinned versions in one batched read."""
        jd_version_id = target.default_jd_version_id
        resume_version_id = target.default_resume_version_id
        rows = (
            await session.execute(
                select(JobDescriptionModel, JobDescriptionVersionModel, ResumeVersionModel)
                .select_from(JobDescriptionModel)
                .outerjoin(
                    JobDescriptionVersionModel,
                    JobDescriptionVersionModel.id == jd_version_id,
                )
                .outerjoin(ResumeVersionModel, ResumeVersionModel.id == resume_version_id)
                .where(JobDescriptionModel.id == target.job_description_id)
            )
        ).first()
        if rows is None:
            return _to_result(target, created=created)
        jd, jd_version, resume_version = rows
        return _to_result(
            target,
            created=created,
            job=JobSummary(id=jd.id, title=jd.title, company=jd.company),
            current_jd_version=(
                JdVersionSummary(
                    id=jd_version.id,
                    version_no=jd_version.version_no,
                    published_at=jd_version.published_at,
                )
                if jd_version is not None
                else None
            ),
            default_resume_version=(
                ResumeVersionSummary(
                    id=resume_version.id,
                    source_type=resume_version.source_type,
                    published_at=resume_version.published_at,
                )
                if resume_version is not None
                else None
            ),
        )

    async def _active_for_jd(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
    ) -> JobTargetModel | None:
        stmt = select(JobTargetModel).where(
            JobTargetModel.job_description_id == jd_id,
            JobTargetModel.archived_at.is_(None),
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _validate_versions(
        self,
        session: AsyncSession,
        jd_id: uuid.UUID,
        jd_version_id: uuid.UUID | None,
        resume_version_id: uuid.UUID | None,
    ) -> None:
        if jd_version_id is not None:
            owner = await self._jd_version_owner(session, jd_version_id)
            if owner != jd_id:
                raise VersionScopeMismatchError("default JD version does not belong to the target's JD identity")
        # Resume version ownership is scoped to the resume/draft, not the JD;
        # any resume version is acceptable for a target. No cross-identity check needed.

    @staticmethod
    async def _jd_version_owner(
        session: AsyncSession,
        version_id: uuid.UUID | None,
    ) -> uuid.UUID | None:
        if version_id is None:
            return None
        version = await session.get(JobDescriptionVersionModel, version_id)
        return version.job_description_id if version else None

    @staticmethod
    async def _resume_version_owner(
        session: AsyncSession,
        version_id: uuid.UUID | None,
    ) -> uuid.UUID | None:
        if version_id is None:
            return None
        version = await session.get(ResumeVersionModel, version_id)
        return version.resume_id or version.draft_id if version else None

    @staticmethod
    def _state(target: JobTargetModel) -> JobTargetState:
        return JobTargetState(
            id=target.id,
            job_description_id=target.job_description_id,
            default_jd_version_id=target.default_jd_version_id,
            default_resume_version_id=target.default_resume_version_id,
            revision=target.revision,
            archived_at=target.archived_at,
        )
