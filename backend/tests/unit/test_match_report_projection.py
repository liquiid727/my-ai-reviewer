"""RIP-014 match assessment report projection rules — pure half (#113, §6.1/§6.3)."""

from __future__ import annotations

from backend.domain.match_assessment.report import (
    action_routes,
    evidence_sufficiency,
    gap_class_counts,
    stale_versions,
)


def _dimension(cited_jd: list[str], cited_resume: list[str]) -> dict:
    return {
        "key": "required_skills",
        "cited_jd_evidence": cited_jd,
        "cited_resume_evidence": cited_resume,
    }


def test_gap_class_counts_buckets_known_classes_and_derived_actions() -> None:
    gaps = [
        {"requirement_id": "jd:1:requirement:a", "category": "capability_gap", "severity": "high"},
        {"requirement_id": "jd:1:requirement:b", "category": "expression_gap", "severity": "medium"},
        {"requirement_id": "jd:1:requirement:c", "category": "evidence_gap", "severity": "low"},
        {"requirement_id": "jd:1:requirement:d", "category": "hard_constraint_risk", "severity": "high"},
        {"requirement_id": "jd:1:requirement:e", "category": "capability_gap", "severity": "low"},
    ]
    counts = gap_class_counts(gaps)
    assert counts["counts_by_class"] == {
        "capability_gap": 2,
        "expression_gap": 1,
        "evidence_gap": 1,
        "hard_constraint_risk": 1,
    }
    assert counts["counts_by_severity"] == {"high": 2, "medium": 1, "low": 2}
    assert counts["counts_by_action_type"] == {"screen": 3, "review": 1, "probe": 1}


def test_gap_class_counts_ignores_unknown_categories_and_missing_severity() -> None:
    counts = gap_class_counts(
        [
            {"requirement_id": "x", "category": "mystery_class"},
            {"requirement_id": "y", "category": "expression_gap"},
        ]
    )
    assert counts["counts_by_class"]["expression_gap"] == 1
    assert counts["counts_by_class"]["capability_gap"] == 0
    assert counts["counts_by_severity"] == {}


def test_gap_class_counts_derives_action_when_missing() -> None:
    counts = gap_class_counts([{"requirement_id": "x", "category": "hard_constraint_risk", "severity": "high"}])
    assert counts["counts_by_action_type"] == {"screen": 1}


def test_evidence_sufficiency_marks_citations_outside_catalog_as_unknown() -> None:
    dimensions = [
        _dimension(cited_jd=["jd:1:requirement:a"], cited_resume=["resume:1:fact:f-1"]),
        _dimension(cited_jd=["jd:1:requirement:a", "jd:1:requirement:ghost"], cited_resume=[]),
    ]
    sufficiency = evidence_sufficiency(
        {"jd_evidence": 3, "resume_evidence": 1},
        dimensions,
        catalog_ids={"jd:1:requirement:a", "resume:1:fact:f-1"},
    )
    assert sufficiency["jd_evidence"] == 3
    assert sufficiency["resume_evidence"] == 1
    assert sorted(sufficiency["cited_ids"]) == [
        "jd:1:requirement:a",
        "jd:1:requirement:ghost",
        "resume:1:fact:f-1",
    ]
    assert sufficiency["unknown_citations"] == ["jd:1:requirement:ghost"]


def test_evidence_sufficiency_dedupes_citations() -> None:
    sufficiency = evidence_sufficiency(
        {},
        [_dimension(cited_jd=["jd:1:requirement:a", "jd:1:requirement:a"], cited_resume=[])],
        catalog_ids={"jd:1:requirement:a"},
    )
    assert sufficiency["cited_ids"] == ["jd:1:requirement:a"]
    assert sufficiency["unknown_citations"] == []


def test_stale_versions_flags_newer_jd_and_moved_target_defaults() -> None:
    stale = stale_versions(
        jd_version_id="jd-v1",
        resume_version_id="res-v1",
        current_jd_version_id="jd-v2",
        target_default_jd_version_id="jd-v2",
        target_default_resume_version_id="res-v1",
    )
    assert stale["jd"] == ["jd_has_newer_published_version", "target_default_jd_version_moved"]
    assert stale["resume"] == []
    assert stale["is_stale"] is True


def test_stale_versions_flags_moved_resume_default() -> None:
    stale = stale_versions(
        jd_version_id="jd-v1",
        resume_version_id="res-v1",
        current_jd_version_id="jd-v1",
        target_default_jd_version_id="jd-v1",
        target_default_resume_version_id="res-v2",
    )
    assert stale["jd"] == []
    assert stale["resume"] == ["target_default_resume_version_moved"]
    assert stale["is_stale"] is True


def test_stale_versions_clean_when_versions_are_current() -> None:
    stale = stale_versions(
        jd_version_id="jd-v1",
        resume_version_id="res-v1",
        current_jd_version_id="jd-v1",
        target_default_jd_version_id="jd-v1",
        target_default_resume_version_id="res-v1",
    )
    assert stale["jd"] == []
    assert stale["resume"] == []
    assert stale["is_stale"] is False


def test_stale_versions_never_clears_flags_when_context_is_missing() -> None:
    stale = stale_versions(
        jd_version_id="jd-v1",
        resume_version_id="res-v1",
        current_jd_version_id=None,
        target_default_jd_version_id=None,
        target_default_resume_version_id=None,
    )
    assert stale["jd"] == []
    assert stale["resume"] == []
    assert stale["is_stale"] is False


def test_action_routes_from_builder_draft_targets_draft() -> None:
    actions = action_routes(
        resume_version_id="res-v1",
        resume_version_source_type="builder_draft",
        parsed_resume_id=None,
        builder_draft_id="draft-9",
    )
    assert [a["id"] for a in actions] == ["resume_optimization"]
    assert actions[0]["route"] == "/builder/:draftId"
    assert actions[0]["destination"] == {"draft_id": "draft-9"}
    assert actions[0]["eligible"] is True


def test_action_routes_from_parsed_resume_offer_plan_and_interview() -> None:
    actions = action_routes(
        resume_version_id="res-v1",
        resume_version_source_type="parsed_resume",
        parsed_resume_id="resume-4",
        builder_draft_id=None,
    )
    assert [a["id"] for a in actions] == ["plan", "interview"]
    assert actions[0]["destination"] == {"resume_id": "resume-4"}
    assert actions[1]["destination"] == {"resume_id": "resume-4"}


def test_action_routes_unknown_source_type_yields_no_actions() -> None:
    actions = action_routes(
        resume_version_id="res-v1",
        resume_version_source_type="legacy",
        parsed_resume_id=None,
        builder_draft_id=None,
    )
    assert actions == []
