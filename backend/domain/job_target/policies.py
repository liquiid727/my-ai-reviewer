"""Job Target domain (RIP-010 §6.3)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


class JobTargetError(Exception):
    """Base Job Target domain error."""


class JobTargetArchivedError(JobTargetError):
    """Mutation targeted an archived workspace."""


class JobTargetRevisionConflictError(JobTargetError):
    """Expected revision is stale."""


class VersionScopeMismatchError(JobTargetError):
    """Default version does not belong to the selected identity."""


@dataclass(frozen=True)
class JobTargetState:
    """Immutable snapshot of a Job Target aggregate for policy evaluation."""

    id: uuid.UUID
    job_description_id: uuid.UUID
    default_jd_version_id: uuid.UUID | None
    default_resume_version_id: uuid.UUID | None
    revision: int
    archived_at: object | None = None

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None


@dataclass(frozen=True)
class DefaultUpdate:
    """Intended default-version mutation."""

    default_jd_version_id: uuid.UUID | None
    default_resume_version_id: uuid.UUID | None


@dataclass
class JobTargetPolicy:
    """Pure rules over Job Target invariants.

    All methods are pure: they validate a proposed mutation against a target
    snapshot and raise on violation without touching storage.
    """

    def validate_ensure(
        self,
        jd_id: uuid.UUID,
        default_jd_version_id: uuid.UUID | None,
        default_resume_version_id: uuid.UUID | None,
        *,
        jd_version_owner: uuid.UUID | None,
        resume_version_owner: uuid.UUID | None,
    ) -> None:
        """Validate version ownership for a target creation/ensure command."""
        if default_jd_version_id is not None and jd_version_owner != jd_id:
            raise VersionScopeMismatchError(
                "default JD version does not belong to the target's JD identity"
            )

    def validate_default_update(
        self,
        current: JobTargetState,
        update: DefaultUpdate,
        expected_revision: int,
        *,
        jd_version_owner: uuid.UUID | None,
        resume_version_owner: uuid.UUID | None,
    ) -> None:
        """Validate a revision-checked default-version update."""
        if current.is_archived:
            raise JobTargetArchivedError("archived target cannot be updated")
        if expected_revision != current.revision:
            raise JobTargetRevisionConflictError(
                f"expected revision {expected_revision}, current {current.revision}"
            )
        if update.default_jd_version_id is not None and jd_version_owner != current.job_description_id:
            raise VersionScopeMismatchError(
                "default JD version does not belong to the target's JD identity"
            )

    def validate_archive(self, current: JobTargetState, expected_revision: int) -> None:
        """Validate a revision-checked archive command."""
        if current.is_archived:
            raise JobTargetArchivedError("target is already archived")
        if expected_revision != current.revision:
            raise JobTargetRevisionConflictError(
                f"expected revision {expected_revision}, current {current.revision}"
            )

    def next_revision(self, current: JobTargetState) -> int:
        return current.revision + 1
