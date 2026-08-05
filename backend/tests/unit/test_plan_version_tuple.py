"""RIP-014 version-pinned plan tuple rules — pure half (#112, §6.2/§7.3)."""

from __future__ import annotations

import uuid

import pytest

from backend.domain.job_search_plan.policies import (
    PlanVersionTupleError,
    build_catalog_from_versions,
    validate_versioned_tuple,
)

A = uuid.uuid4()
B = uuid.uuid4()


def _assert_kind(kind: str, fn) -> None:
    with pytest.raises(PlanVersionTupleError) as excinfo:
        fn()
    assert excinfo.value.kind == kind


def test_coherent_tuple_passes() -> None:
    validate_versioned_tuple(
        target_id=A,
        target_jd_id=A,
        target_resume_id=A,
        jd_version_owner=A,
        resume_version_owner=A,
        assessment_status="completed",
        assessment_target_id=A,
        assessment_jd_version_id=A,
        assessment_resume_version_id=A,
        requested_match_assessment_id=A,
        requested_jd_version_id=A,
        requested_resume_version_id=A,
    )


def test_target_identity_mismatch_is_scope() -> None:
    _assert_kind(
        "scope",
        lambda: validate_versioned_tuple(
            target_id=A,
            target_jd_id=A,
            target_resume_id=A,
            jd_version_owner=B,
            resume_version_owner=A,
            assessment_status="completed",
            assessment_target_id=A,
            assessment_jd_version_id=A,
            assessment_resume_version_id=A,
            requested_match_assessment_id=A,
            requested_jd_version_id=A,
            requested_resume_version_id=A,
        ),
    )


def test_version_owner_mismatch_is_scope() -> None:
    _assert_kind(
        "scope",
        lambda: validate_versioned_tuple(
            target_id=A,
            target_jd_id=A,
            target_resume_id=A,
            jd_version_owner=A,
            resume_version_owner=B,
            assessment_status="completed",
            assessment_target_id=A,
            assessment_jd_version_id=A,
            assessment_resume_version_id=A,
            requested_match_assessment_id=A,
            requested_jd_version_id=A,
            requested_resume_version_id=A,
        ),
    )


def test_missing_assessment_is_assessment() -> None:
    _assert_kind(
        "assessment",
        lambda: validate_versioned_tuple(
            target_id=A,
            target_jd_id=A,
            target_resume_id=A,
            jd_version_owner=A,
            resume_version_owner=A,
            assessment_status=None,
            assessment_target_id=None,
            assessment_jd_version_id=None,
            assessment_resume_version_id=None,
            requested_match_assessment_id=None,
            requested_jd_version_id=A,
            requested_resume_version_id=A,
        ),
    )


def test_unfinished_assessment_is_assessment() -> None:
    _assert_kind(
        "assessment",
        lambda: validate_versioned_tuple(
            target_id=A,
            target_jd_id=A,
            target_resume_id=A,
            jd_version_owner=A,
            resume_version_owner=A,
            assessment_status="failed",
            assessment_target_id=A,
            assessment_jd_version_id=A,
            assessment_resume_version_id=A,
            requested_match_assessment_id=A,
            requested_jd_version_id=A,
            requested_resume_version_id=A,
        ),
    )


def test_assessment_pinned_to_other_versions_is_assessment() -> None:
    _assert_kind(
        "assessment",
        lambda: validate_versioned_tuple(
            target_id=A,
            target_jd_id=A,
            target_resume_id=A,
            jd_version_owner=A,
            resume_version_owner=A,
            assessment_status="completed",
            assessment_target_id=A,
            assessment_jd_version_id=B,
            assessment_resume_version_id=A,
            requested_match_assessment_id=A,
            requested_jd_version_id=A,
            requested_resume_version_id=A,
        ),
    )
    _assert_kind(
        "assessment",
        lambda: validate_versioned_tuple(
            target_id=A,
            target_jd_id=A,
            target_resume_id=A,
            jd_version_owner=A,
            resume_version_owner=A,
            assessment_status="completed",
            assessment_target_id=A,
            assessment_jd_version_id=A,
            assessment_resume_version_id=B,
            requested_match_assessment_id=A,
            requested_jd_version_id=A,
            requested_resume_version_id=A,
        ),
    )


def test_snapshot_catalog_is_deterministic_and_identity_free() -> None:
    jd_structured = {
        "required_skills": [
            {"key": "sk-1", "value": "Go", "evidence": "精通 Go"},
            {"key": "sk-2", "value": "Kubernetes", "evidence": "K8s 运维"},
        ],
        "responsibilities": [{"key": "res-1", "value": "设计服务", "evidence": "服务设计"}],
    }
    # Canonical resume versions are privacy-masked at publish time (the
    # PrivacyGuard rejects unmasked snapshots); the catalog copies the same
    # masked evidence the match assessment was built on.
    profile = {
        "skills": [{"name": "Go", "evidence": "Go 项目经验 4 年", "confidence": 0.9}],
        "title": "资深后端工程师",
    }
    facts = [{"key": "f-1", "value": "Go", "evidence": {"source_text": "Go 项目"}}]

    first = build_catalog_from_versions(
        jd_version_id=str(A),
        jd_structured=jd_structured,
        resume_version_id=str(B),
        resume_profile=profile,
        resume_facts=facts,
    )
    second = build_catalog_from_versions(
        jd_version_id=str(A),
        jd_structured=jd_structured,
        resume_version_id=str(B),
        resume_profile=profile,
        resume_facts=facts,
    )
    assert first == second
    assert [entry.id for entry in first] == [entry.id for entry in second]
    assert len(first) == len({entry.id for entry in first})

    serialized = "".join(f"{entry.id}|{entry.label}|{entry.excerpt}" for entry in first)
    # The JD requirement evidence survives masked as the excerpt.
    assert "精通 Go" in serialized
    # Identity fields that could exist in an unmasked profile never enter the
    # catalog: the builder reads only skills/title/summary/location/facts.
    profile_with_identity = {
        **profile,
        "name": "Alice Private",
        "email": "alice@example.com",
        "phone": "13800138000",
    }
    with_identity = build_catalog_from_versions(
        jd_version_id=str(A),
        jd_structured=jd_structured,
        resume_version_id=str(B),
        resume_profile=profile_with_identity,
        resume_facts=facts,
    )
    assert with_identity == first
