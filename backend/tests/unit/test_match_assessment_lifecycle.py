"""Match Assessment lifecycle tests (RIP-013 §6.1, §7.1, §7.2, §11)."""

from __future__ import annotations

import uuid

import pytest

from backend.domain.match_assessment.lifecycle import (
    ACTIVE_STATUSES,
    TERMINAL_STATUSES,
    VALID_STATUSES,
    Failure,
    MatchActiveExistsError,
    MatchAssessmentState,
    MatchAssessmentTuple,
    MatchCompletedImmutabilityError,
    MatchInvalidStateError,
    MatchLifecycle,
    MatchRetryNotAllowedError,
    MatchScopeMismatchError,
    MatchStaleRunError,
    has_result,
)

_JT = uuid.uuid4()
_JDV = uuid.uuid4()
_RSV = uuid.uuid4()


def _state(
    *,
    status: str = "queued",
    run_id: uuid.UUID | None = None,
    attempt: int = 1,
    total_score: object | None = None,
    completed_at: object | None = None,
) -> MatchAssessmentState:
    return MatchAssessmentState(
        id=uuid.uuid4(),
        job_target_id=_JT,
        jd_version_id=_JDV,
        resume_version_id=_RSV,
        status=status,
        policy_version="match-v1",
        run_id=run_id or uuid.uuid4(),
        attempt=attempt,
        retryable=False,
        total_score=total_score,
        completed_at=completed_at,
    )


def _tuple() -> MatchAssessmentTuple:
    return MatchAssessmentTuple(
        job_target_id=_JT,
        jd_version_id=_JDV,
        resume_version_id=_RSV,
        policy_version="match-v1",
    )


def test_status_fixture_complete() -> None:
    assert VALID_STATUSES == ("queued", "evaluating", "completed", "failed")
    assert ACTIVE_STATUSES == ("queued", "evaluating")
    assert TERMINAL_STATUSES == ("completed", "failed")


def test_scope_mismatch_rejected() -> None:
    policy = MatchLifecycle()
    with pytest.raises(MatchScopeMismatchError):
        policy.validate_scope(target_jd_id=_JT, jd_version_owner=uuid.uuid4())
    # matching owner passes silently
    policy.validate_scope(target_jd_id=_JT, jd_version_owner=_JT)


def test_create_no_existing_creates_new_run() -> None:
    policy = MatchLifecycle()
    reuse, run_id = policy.pick_create(tuple_=_tuple(), existing=None, force=False)
    assert reuse is False
    assert isinstance(run_id, uuid.UUID)


def test_create_reuses_completed_unless_force() -> None:
    policy = MatchLifecycle()
    completed = _state(status="completed", run_id=uuid.uuid4(), total_score=72.0)
    reuse, run_id = policy.pick_create(tuple_=_tuple(), existing=completed, force=False)
    assert reuse is True
    assert run_id == completed.run_id
    reuse_forced, new_run = policy.pick_create(tuple_=_tuple(), existing=completed, force=True)
    assert reuse_forced is False
    assert new_run != completed.run_id


def test_create_never_reuses_failed() -> None:
    policy = MatchLifecycle()
    failed = _state(status="failed", run_id=uuid.uuid4())
    reuse, run_id = policy.pick_create(tuple_=_tuple(), existing=failed, force=False)
    assert reuse is False
    assert run_id != failed.run_id


def test_create_rejects_active_duplicate() -> None:
    policy = MatchLifecycle()
    for status in ("queued", "evaluating"):
        active = _state(status=status)
        with pytest.raises(MatchActiveExistsError):
            policy.pick_create(tuple_=_tuple(), existing=active, force=False)
        with pytest.raises(MatchActiveExistsError):
            policy.pick_create(tuple_=_tuple(), existing=active, force=True)


def test_queued_to_evaluating_requires_owner_run() -> None:
    policy = MatchLifecycle()
    state = _state(status="queued")
    policy.start_evaluating(state, run_id=state.run_id)
    with pytest.raises(MatchStaleRunError):
        policy.start_evaluating(state, run_id=uuid.uuid4())
    evaluating = _state(status="evaluating")
    with pytest.raises(MatchInvalidStateError):
        policy.start_evaluating(evaluating, run_id=evaluating.run_id)


def test_evaluating_to_completed_immutable() -> None:
    policy = MatchLifecycle()
    evaluating = _state(status="evaluating", total_score=None)
    policy.complete(evaluating, run_id=evaluating.run_id)
    with pytest.raises(MatchStaleRunError):
        policy.complete(evaluating, run_id=uuid.uuid4())
    with pytest.raises(MatchInvalidStateError):
        policy.complete(_state(status="queued"), run_id=evaluating.run_id)
    # a completed snapshot already carrying a score can never be re-completed
    completed = _state(status="completed", total_score=72.0, run_id=uuid.uuid4())
    with pytest.raises(MatchCompletedImmutabilityError):
        policy.complete(completed, run_id=completed.run_id)


def test_evaluating_to_failed_safe_diagnostic() -> None:
    policy = MatchLifecycle()
    evaluating = _state(status="evaluating")
    failure = Failure(code="ASSESSMENT_FAILED", details="broker down", retryable=True)
    policy.fail(evaluating, run_id=evaluating.run_id, failure=failure)
    with pytest.raises(MatchStaleRunError):
        policy.fail(evaluating, run_id=uuid.uuid4(), failure=failure)
    with pytest.raises(MatchInvalidStateError):
        policy.fail(_state(status="completed", total_score=1.0), run_id=uuid.uuid4(), failure=failure)


def test_retry_only_from_failed_new_run_same_row() -> None:
    policy = MatchLifecycle()
    failed = _state(status="failed", run_id=uuid.uuid4(), attempt=2)
    new_run, attempt = policy.retry(failed)
    assert new_run != failed.run_id
    assert attempt == 3
    for status in ("queued", "evaluating", "completed"):
        with pytest.raises(MatchRetryNotAllowedError):
            policy.retry(_state(status=status, total_score=72.0 if status == "completed" else None))


def test_has_result_requires_completed_score() -> None:
    assert has_result(_state(status="completed", total_score=72.0)) is True
    assert has_result(_state(status="completed", total_score=None)) is False
    assert has_result(_state(status="evaluating")) is False
    assert has_result(_state(status="failed")) is False
