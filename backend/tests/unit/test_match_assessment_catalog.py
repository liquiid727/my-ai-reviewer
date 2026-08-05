"""Source Catalog normalization tests (RIP-013 §6.2)."""

from __future__ import annotations

import pytest

from backend.domain.match_assessment.source_catalog import build_catalog

JD_VERSION_ID = "jd-v1"
RESUME_VERSION_ID = "res-v1"


def _jd_structured() -> dict:
    return {
        "required_skills": [
            {"key": "sk-1", "value": "Python", "evidence": "Python is required", "confidence": 0.95},
            {"key": "sk-2", "value": "AWS", "evidence": None, "confidence": 0.8},
        ],
        "responsibilities": [
            {
                "key": "res-1",
                "value": "Own the data pipeline",
                "evidence": "Own the data pipeline",
                "confidence": 0.9,
            }
        ],
    }


def _resume_snapshot() -> tuple[dict, list]:
    profile = {
        "title": "Senior Data Engineer",
        "summary": "Built pipelines for 5 years",
        "location": "Shanghai",
        "skills": [
            {"name": "Python", "evidence": "Used Python daily", "confidence": 0.9},
            {"name": "JS", "evidence": None, "confidence": 0.5},
        ],
        "projects": [
            {"name": "ETL Rewrite", "background": "Legacy pipeline", "responsibility": "Rebuilt ingestion"}
        ],
    }
    facts = [
        {
            "fact_type": "work_experience",
            "key": "fact-1",
            "value": "Data Engineer at Acme",
            "evidence": {
                "source_text": "Data Engineer, Acme 2021-2024",
                "section": "work_experience",
                "confidence": 0.9,
            },
        },
        {
            "fact_type": "skill",
            "key": "fact-2",
            "value": "SQL",
            "evidence": {"source_text": "Proficient in SQL", "section": "skills", "confidence": 0.8},
        },
    ]
    return profile, facts


def test_catalog_builds_typed_items() -> None:
    profile, facts = _resume_snapshot()
    catalog = build_catalog(
        jd_version_id=JD_VERSION_ID,
        jd_structured=_jd_structured(),
        resume_version_id=RESUME_VERSION_ID,
        resume_profile=profile,
        resume_facts=facts,
    )
    assert len(catalog.items) == 11
    kinds = {item.kind for item in catalog.items}
    assert kinds == {"requirement", "responsibility", "fact", "project", "profile"}


def test_catalog_ids_follow_spec_shapes() -> None:
    profile, facts = _resume_snapshot()
    catalog = build_catalog(
        jd_version_id=JD_VERSION_ID,
        jd_structured=_jd_structured(),
        resume_version_id=RESUME_VERSION_ID,
        resume_profile=profile,
        resume_facts=facts,
    )
    ids = catalog.ids()
    assert "jd:jd-v1:requirement:sk-1" in ids
    assert "jd:jd-v1:requirement:sk-2" in ids
    assert "jd:jd-v1:responsibility:res-1" in ids
    assert "resume:res-v1:fact:fact-1" in ids
    assert "resume:res-v1:fact:fact-2" in ids
    assert "resume:res-v1:project:0" in ids
    assert "resume:res-v1:profile:title" in ids
    assert "resume:res-v1:profile:summary" in ids
    assert "resume:res-v1:profile:location" in ids


def test_catalog_carries_masked_excerpts_and_provenance() -> None:
    profile, facts = _resume_snapshot()
    catalog = build_catalog(
        jd_version_id=JD_VERSION_ID,
        jd_structured=_jd_structured(),
        resume_version_id=RESUME_VERSION_ID,
        resume_profile=profile,
        resume_facts=facts,
    )
    item = catalog.by_id("jd:jd-v1:requirement:sk-1")
    assert item is not None
    assert item.masked_excerpt == "Python is required"
    assert item.provenance == "source"
    assert item.confidence == pytest.approx(0.95)
    item = catalog.by_id("resume:res-v1:fact:fact-1")
    assert item is not None
    assert item.masked_excerpt == "Data Engineer, Acme 2021-2024"


def test_catalog_requirement_without_evidence_has_none_excerpt() -> None:
    profile, facts = _resume_snapshot()
    catalog = build_catalog(
        jd_version_id=JD_VERSION_ID,
        jd_structured=_jd_structured(),
        resume_version_id=RESUME_VERSION_ID,
        resume_profile=profile,
        resume_facts=facts,
    )
    item = catalog.by_id("jd:jd-v1:requirement:sk-2")
    assert item is not None
    assert item.masked_excerpt is None


def test_catalog_normalizes_skill_claims() -> None:
    profile, facts = _resume_snapshot()
    catalog = build_catalog(
        jd_version_id=JD_VERSION_ID,
        jd_structured=_jd_structured(),
        resume_version_id=RESUME_VERSION_ID,
        resume_profile=profile,
        resume_facts=facts,
    )
    item = catalog.by_id("resume:res-v1:fact:skill-1")
    assert item is not None
    assert item.claim == "javascript"
    assert item.masked_excerpt is None
    assert item.confidence == pytest.approx(0.5)

    item = catalog.by_id("resume:res-v1:fact:skill-0")
    assert item is not None
    assert item.claim == "python"
    assert item.masked_excerpt == "Used Python daily"


def test_catalog_skips_missing_values_and_bad_rows() -> None:
    profile, facts = _resume_snapshot()
    profile["skills"] = [{"name": "", "evidence": None, "confidence": 0.0}]
    catalog = build_catalog(
        jd_version_id=JD_VERSION_ID,
        jd_structured={
            "required_skills": [{"key": "sk-1", "value": "", "evidence": None, "confidence": 0.0}],
            "responsibilities": [],
        },
        resume_version_id=RESUME_VERSION_ID,
        resume_profile=profile,
        resume_facts=[],
    )
    assert len(catalog.items) == 4  # project + the three profile claims


def test_catalog_by_id_and_ids_consistent() -> None:
    profile, facts = _resume_snapshot()
    catalog = build_catalog(
        jd_version_id=JD_VERSION_ID,
        jd_structured=_jd_structured(),
        resume_version_id=RESUME_VERSION_ID,
        resume_profile=profile,
        resume_facts=facts,
    )
    for item_id in catalog.ids():
        assert catalog.by_id(item_id) is not None
    assert catalog.by_id("jd:unknown:requirement:x") is None
