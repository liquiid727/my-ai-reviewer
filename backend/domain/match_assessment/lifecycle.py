"""Match Assessment lifecycle rules (RIP-013 §6.1, §7.1, §7.2).

Pure transition rules over an assessment snapshot: queued/evaluating/
completed/failed transitions, completed immutability, normal reuse,
force-new-row, failed retry, and stale-run ownership. No storage, HTTP,
Celery, or LLM imports.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

ACTIVE_STATUSES: tuple[str, ...] = ("queued", "evaluating")
TERMINAL_STATUSES: tuple[str, ...] = ("completed", "failed")
VALID_STATUSES: tuple[str, ...] = (*ACTIVE_STATUSES, *TERMINAL_STATUSES)


class MatchLifecycleError(Exception):
    """Base Match Assessment lifecycle error."""


class MatchInvalidStateError(MatchLifecycleError):
    """A transition is not allowed from the current status."""


class MatchCompletedImmutabilityError(MatchLifecycleError):
    """A mutation targeted a completed assessment."""


class MatchActiveExistsError(MatchLifecycleError):
    """An active (queued/evaluating) assessment already exists for the tuple."""


class MatchRetryNotAllowedError(MatchLifecycleError):
    """Retry is allowed only from failed."""


class MatchStaleRunError(MatchLifecycleError):
    """The worker run no longer owns the assessment."""


class MatchScopeMismatchError(MatchLifecycleError):
    """A version does not belong to the target's JD identity."""


@dataclass(frozen=True)
class MatchAssessmentState:
    """Immutable snapshot of an assessment aggregate for policy evaluation."""

    id: uuid.UUID
    job_target_id: uuid.UUID
    jd_version_id: uuid.UUID
    resume_version_id: uuid.UUID
    status: str
    policy_version: str
    run_id: uuid.UUID
    attempt: int = 1
    retryable: bool = False
    total_score: object | None = None
    completed_at: object | None = None

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"


@dataclass(frozen=True)
class MatchAssessmentTuple:
    """Identity of an assessment run: exact versions under one policy."""

    job_target_id: uuid.UUID
    jd_version_id: uuid.UUID
    resume_version_id: uuid.UUID
    policy_version: str


@dataclass(frozen=True)
class Failure:
    """Safe terminal diagnostic persisted on failed assessments."""

    code: str
    details: str = ""
    retryable: bool = False


@dataclass
class MatchLifecycle:
    """Pure rules over Match Assessment invariants (RIP-013 §6.1, §7.2)."""

    def validate_scope(
        self,
        *,
        target_jd_id: uuid.UUID,
        jd_version_owner: uuid.UUID,
    ) -> None:
        """Reject a JD version that does not belong to the target's JD identity."""
        if jd_version_owner != target_jd_id:
            raise MatchScopeMismatchError(
                "JD version does not belong to the target's JD identity"
            )

    def pick_create(
        self,
        *,
        tuple_: MatchAssessmentTuple,
        existing: MatchAssessmentState | None,
        force: bool,
    ) -> tuple[bool, uuid.UUID]:
        """Decide whether a create command reuses or inserts a new assessment.

        Returns (reuse, run_id); reuse implies the caller returns the existing
        completed assessment untouched. Raises when an active row already
        exists for the tuple.
        """
        if existing is None:
            return False, uuid.uuid4()
        if existing.is_active:
            raise MatchActiveExistsError(
                "an assessment is already running for this version/policy tuple"
            )
        if existing.is_completed and not force:
            return True, existing.run_id
        return False, uuid.uuid4()

    def start_evaluating(
        self,
        current: MatchAssessmentState,
        *,
        run_id: uuid.UUID,
    ) -> None:
        """queued -> evaluating. The worker must own the current run."""
        if current.status != "queued":
            raise MatchInvalidStateError(
                f"cannot start evaluating from status {current.status}"
            )
        if run_id != current.run_id:
            raise MatchStaleRunError("run id is no longer the current run")

    def complete(
        self,
        current: MatchAssessmentState,
        *,
        run_id: uuid.UUID,
    ) -> None:
        """evaluating -> completed. Completed results are immutable."""
        if current.total_score is not None:
            raise MatchCompletedImmutabilityError("completed assessment is immutable")
        if current.status != "evaluating":
            raise MatchInvalidStateError(
                f"cannot complete from status {current.status}"
            )
        if run_id != current.run_id:
            raise MatchStaleRunError("run id is no longer the current run")

    def fail(
        self,
        current: MatchAssessmentState,
        *,
        run_id: uuid.UUID,
        failure: Failure,
    ) -> None:
        """evaluating -> failed with a safe diagnostic; only the owning run."""
        if current.status != "evaluating":
            raise MatchInvalidStateError(f"cannot fail from status {current.status}")
        if run_id != current.run_id:
            raise MatchStaleRunError("run id is no longer the current run")

    def retry(
        self,
        current: MatchAssessmentState,
    ) -> tuple[uuid.UUID, int]:
        """failed -> queued on the same row with a new run id and cleared failure.

        Returns (new_run_id, next_attempt). Retry is allowed only for failed
        assessments; completion is never mutated in place.
        """
        if current.status != "failed":
            raise MatchRetryNotAllowedError(
                f"retry is allowed only from failed, not {current.status}"
            )
        return uuid.uuid4(), current.attempt + 1


def has_result(state: MatchAssessmentState) -> bool:
    """Whether the snapshot carries a completed result."""
    return state.is_completed and state.total_score is not None
