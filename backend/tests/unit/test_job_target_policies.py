"""Job Target domain policy tests (RIP-010 #093)."""

from __future__ import annotations

import uuid

import pytest

from backend.domain.job_target.policies import (
    DefaultUpdate,
    JobTargetArchivedError,
    JobTargetPolicy,
    JobTargetRevisionConflictError,
    JobTargetState,
    VersionScopeMismatchError,
)


def _state(**overrides) -> JobTargetState:
    base = dict(
        id=uuid.uuid4(),
        job_description_id=uuid.uuid4(),
        default_jd_version_id=None,
        default_resume_version_id=None,
        revision=1,
        archived_at=None,
    )
    base.update(overrides)
    return JobTargetState(**base)


def test_ensure_accepts_null_defaults() -> None:
    policy = JobTargetPolicy()
    jd_id = uuid.uuid4()
    policy.validate_ensure(jd_id, None, None, jd_version_owner=None, resume_version_owner=None)


def test_ensure_rejects_cross_identity_jd_version() -> None:
    policy = JobTargetPolicy()
    jd_id = uuid.uuid4()
    other_jd = uuid.uuid4()
    with pytest.raises(VersionScopeMismatchError):
        policy.validate_ensure(
            jd_id,
            uuid.uuid4(),
            None,
            jd_version_owner=other_jd,
            resume_version_owner=None,
        )


def test_ensure_accepts_matching_owner() -> None:
    policy = JobTargetPolicy()
    jd_id = uuid.uuid4()
    jd_version = uuid.uuid4()
    policy.validate_ensure(jd_id, jd_version, None, jd_version_owner=jd_id, resume_version_owner=None)


def test_update_revision_conflict() -> None:
    policy = JobTargetPolicy()
    state = _state(revision=3)
    with pytest.raises(JobTargetRevisionConflictError):
        policy.validate_default_update(
            state,
            DefaultUpdate(None, None),
            expected_revision=2,
            jd_version_owner=None,
            resume_version_owner=None,
        )


def test_update_archived_rejected() -> None:
    policy = JobTargetPolicy()
    state = _state(archived_at=object())
    with pytest.raises(JobTargetArchivedError):
        policy.validate_default_update(
            state,
            DefaultUpdate(None, None),
            expected_revision=1,
            jd_version_owner=None,
            resume_version_owner=None,
        )


def test_update_rejects_cross_identity_jd_version() -> None:
    policy = JobTargetPolicy()
    state = _state()
    with pytest.raises(VersionScopeMismatchError):
        policy.validate_default_update(
            state,
            DefaultUpdate(uuid.uuid4(), None),
            expected_revision=1,
            jd_version_owner=uuid.uuid4(),
            resume_version_owner=None,
        )


def test_update_accepts_matching_owner() -> None:
    policy = JobTargetPolicy()
    state = _state()
    jd_version = uuid.uuid4()
    policy.validate_default_update(
        state,
        DefaultUpdate(jd_version, None),
        expected_revision=1,
        jd_version_owner=state.job_description_id,
        resume_version_owner=None,
    )


def test_archive_revision_conflict() -> None:
    policy = JobTargetPolicy()
    state = _state(revision=5)
    with pytest.raises(JobTargetRevisionConflictError):
        policy.validate_archive(state, expected_revision=4)


def test_archive_already_archived() -> None:
    policy = JobTargetPolicy()
    state = _state(archived_at=object())
    with pytest.raises(JobTargetArchivedError):
        policy.validate_archive(state, expected_revision=1)


def test_next_revision_increments() -> None:
    policy = JobTargetPolicy()
    assert policy.next_revision(_state(revision=1)) == 2


def test_archived_flag() -> None:
    assert not _state().is_archived
    assert _state(archived_at=object()).is_archived
