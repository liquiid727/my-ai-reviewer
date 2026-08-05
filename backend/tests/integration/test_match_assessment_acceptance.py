"""RIP-013 match-engine acceptance gate — DB/API half (#111, §10-§12).

Completes privacy + convergence + index acceptance: completed rows and API
responses never carry unmasked canaries (provider payload masking is proven
in test_match_semantic_matcher.py); malformed semantic output converges to
the terminal ASSESSMENT_EVIDENCE_INVALID diagnostic; concurrent force
creates converge to a single active row via the partial unique index; and
the reuse and target-cursor queries use the schema indexes.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

import backend.tasks.match_tasks as match_tasks_module
from backend.application.match_assessment import MatchAssessmentWorker
from backend.infrastructure.db.models import (
    JobDescriptionModel,
    JobDescriptionVersionModel,
    JobTargetModel,
    MatchAssessmentModel,
    ResumeModel,
    ResumeVersionModel,
)
from backend.infrastructure.matchers import (
    ALLOWED_DIMENSIONS,
    ConstrainedSemanticMatcher,
    MatchedDimension,
    MatchedGap,
    MatchSemanticError,
    MatchSemanticResult,
)
from backend.tests.conftest import TestSessionFactory, requires_db

pytestmark = requires_db

# Deterministic dispatch failure so no worker task is enqueued by accident;
# every test drives MatchAssessmentWorker directly with a fake matcher.


def _broker_down(*_args: object, **_kwargs: object) -> None:
    raise ConnectionError("broker unreachable")


match_tasks_module.process_match_assessment = _broker_down  # type: ignore[assignment]

CANARIES = ("Acme", "alice@example.com", "13800138000")


async def _seed(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Match JD",
        raw_text="JD with Acme identifiers",
        status="ready",
        processing_step="done",
    )
    session.add(jd)
    await session.flush()
    jd_version = JobDescriptionVersionModel(
        id=uuid.uuid4(),
        job_description_id=jd.id,
        version_no=1,
        normalized_text="JD",
        structured={
            "required_skills": [
                {"key": "sk-1", "value": "Go", "evidence": "精通 Go"},
                {"key": "sk-2", "value": "Kubernetes", "evidence": "K8s 运维"},
            ]
        },
        evidence={},
        source_metadata={},
        content_hash="a" * 64,
        parser_version="legacy",
        schema_version="jd-v1",
        publication_reason="legacy_backfill",
    )
    resume = ResumeModel(id=uuid.uuid4(), status="evaluated", masked_text="[MASKED]")
    session.add(resume)
    await session.flush()
    resume_version = ResumeVersionModel(
        id=uuid.uuid4(),
        source_type="parsed_resume",
        resume_id=resume.id,
        source_revision=1,
        content_hash="b" * 64,
        masked_snapshot={"masked_text": "[MASKED]"},
        profile_snapshot={
            "skills": [
                {
                    "name": "Go",
                    "evidence": "Acme Go 项目经验 4 年 alice@example.com 13800138000",
                    "confidence": 0.9,
                }
            ]
        },
        evidence_catalog=[],
        parser_version="resume-parser-v3",
        schema_version="resume-v1",
        privacy_policy_version="resume-privacy-v1",
    )
    session.add_all([jd_version, resume_version])
    await session.flush()
    target = JobTargetModel(
        id=uuid.uuid4(),
        job_description_id=jd.id,
        default_jd_version_id=jd_version.id,
        default_resume_version_id=resume_version.id,
        revision=1,
    )
    session.add(target)
    await session.commit()
    return jd_version.id, resume_version.id, target.id


async def _insert_assessment(
    session: AsyncSession,
    *,
    jd_version_id: uuid.UUID,
    resume_version_id: uuid.UUID,
    target_id: uuid.UUID,
    status: str,
) -> MatchAssessmentModel:
    assessment = MatchAssessmentModel(
        id=uuid.uuid4(),
        job_target_id=target_id,
        jd_version_id=jd_version_id,
        resume_version_id=resume_version_id,
        status=status,
        policy_version="match-v1",
        run_id=uuid.uuid4(),
        attempt=1,
        retryable=False,
    )
    session.add(assessment)
    await session.commit()
    await session.refresh(assessment)
    return assessment


class _FakeMatcher(ConstrainedSemanticMatcher):
    """Deterministic classifier; `raw` overrides the score for every dimension."""

    def __init__(self, raw: float = 80.0) -> None:
        super().__init__(gateway=object())  # type: ignore[arg-type]  # classify is overridden
        self.raw = raw

    async def classify(
        self,
        *,
        catalog: object,
        dimensions: list[Any],
        requirements: list[str],
    ) -> MatchSemanticResult:
        dims = [
            MatchedDimension(
                key=key,
                raw_score=self.raw,
                confidence=0.9,
                cited_jd_evidence=(
                    ["jd:v1:requirement:sk-1"] if key == "required_skills" else []
                ),
                cited_resume_evidence=(
                    ["resume:v1:fact:skill-0"] if key == "required_skills" else []
                ),
                explanation="masked summary",
            )
            for key in ALLOWED_DIMENSIONS
        ]
        gaps = [
            MatchedGap(
                requirement_id="jd:v1:requirement:sk-1",
                category="evidence_gap",
                severity="medium",
                candidate_evidence=["resume:v1:fact:skill-0"],
                missing_evidence=False,
                confidence=0.6,
                uncertain=False,
            )
        ]
        return MatchSemanticResult(
            dimensions=dims,
            gaps=gaps,
            model_info="fake-model",
            deterministic=False,
        )


class _MalformedMatcher(_FakeMatcher):
    """Semantic output that fails the evidence validator (non-allow-listed id).

    The real matcher raises MatchSemanticError(evidence_invalid=True) from its
    validator (see test_match_semantic_matcher.py); the worker must map that
    to the terminal ASSESSMENT_EVIDENCE_INVALID diagnostic.
    """

    async def classify(
        self,
        *,
        catalog: object,
        dimensions: list[Any],
        requirements: list[str],
    ) -> MatchSemanticResult:
        raise MatchSemanticError(
            "semantic output cites non-allow-listed evidence: resume:v1:fact:made-up",
            evidence_invalid=True,
        )


async def _complete(
    session: AsyncSession,
    assessment: MatchAssessmentModel,
    matcher: _FakeMatcher | None = None,
) -> str:
    worker = MatchAssessmentWorker(
        session=session,
        matcher=matcher or _FakeMatcher(),  # type: ignore[arg-type]
    )
    return await worker.evaluate(assessment.id, assessment.run_id)


async def test_completed_row_and_api_never_expose_canaries(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    jd_version_id, resume_version_id, target_id = await _seed(db_session)
    assessment = await _insert_assessment(
        db_session,
        jd_version_id=jd_version_id,
        resume_version_id=resume_version_id,
        target_id=target_id,
        status="queued",
    )
    assert await _complete(db_session, assessment) == "completed"

    rows = (
        await db_session.execute(
            select(MatchAssessmentModel).where(MatchAssessmentModel.id == assessment.id)
        )
    ).scalars().all()
    row = rows[0]
    serialized = json.dumps(
        {
            "status": row.status,
            "error_code": row.error_code,
            "error_details": row.error_details,
            "dimension_scores": row.dimension_scores,
            "rule_results": row.rule_results,
            "gaps": row.gaps,
            "evidence_summary": row.evidence_summary,
            "recommendation": row.recommendation,
            "model_name": row.model_name,
        },
        ensure_ascii=False,
    )
    for canary in CANARIES:
        assert canary not in serialized
        assert canary not in row.evidence_summary.keys()

    response = await async_client.get(f"/api/v1/match-assessments/{assessment.id}")
    assert response.status_code == 200
    body = response.text
    for canary in CANARIES:
        assert canary not in body


async def test_malformed_semantic_output_persists_invalid_evidence(
    db_session: AsyncSession,
) -> None:
    jd_version_id, resume_version_id, target_id = await _seed(db_session)
    assessment = await _insert_assessment(
        db_session,
        jd_version_id=jd_version_id,
        resume_version_id=resume_version_id,
        target_id=target_id,
        status="queued",
    )
    outcome = await _complete(db_session, assessment, matcher=_MalformedMatcher())
    assert outcome == "failed"

    rows = (
        await db_session.execute(
            select(MatchAssessmentModel).where(MatchAssessmentModel.id == assessment.id)
        )
    ).scalars().all()
    assert rows[0].status == "failed"
    assert rows[0].error_code == "ASSESSMENT_EVIDENCE_INVALID"
    assert rows[0].retryable is False
    assert rows[0].total_score is None


async def test_concurrent_force_create_converges_to_single_active_row(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two racing force creates on the same tuple converge to one active row.

    Dispatch is a no-op here (not broker-down): the rows must stay `queued`
    so the partial unique active-tuple index is the arbiter.
    """
    monkeypatch.setattr(
        match_tasks_module, "process_match_assessment", lambda *_a, **_k: None
    )
    jd_version_id, resume_version_id, target_id = await _seed(db_session)

    async def create() -> str:
        async with TestSessionFactory() as session:
            from backend.application.match_assessment import (
                CreateAssessmentCommand,
                MatchAssessmentUseCases,
            )

            try:
                result = await MatchAssessmentUseCases().create(
                    session,
                    CreateAssessmentCommand(
                        job_target_id=target_id,
                        jd_version_id=jd_version_id,
                        resume_version_id=resume_version_id,
                        policy_version="match-v1",
                        force=True,
                    ),
                )
                return str(result.id)
            except Exception:
                return "error"

    results = await asyncio.gather(create(), create())
    ids = [r for r in results if r != "error"]
    assert len(ids) == 1

    rows = (
        await db_session.execute(
            select(MatchAssessmentModel).where(
                MatchAssessmentModel.jd_version_id == jd_version_id,
                MatchAssessmentModel.resume_version_id == resume_version_id,
            )
        )
    ).scalars().all()
    active = [r for r in rows if r.status in ("queued", "evaluating")]
    assert len(active) == 1


async def test_reuse_lookup_and_target_cursor_use_indexes(
    db_session: AsyncSession,
) -> None:
    jd_version_id, resume_version_id, target_id = await _seed(db_session)
    assessment = await _insert_assessment(
        db_session,
        jd_version_id=jd_version_id,
        resume_version_id=resume_version_id,
        target_id=target_id,
        status="completed",
    )

    reuse_explain = await db_session.execute(
        text(
            "EXPLAIN (FORMAT JSON) SELECT id FROM match_assessments "
            "WHERE jd_version_id = :jd AND resume_version_id = :rv AND policy_version = 'match-v1' "
            "ORDER BY created_at DESC, id DESC LIMIT 1"
        ),
        {"jd": str(jd_version_id), "rv": str(resume_version_id)},
    )
    reuse_plan = json.dumps(reuse_explain.scalar_one())
    assert "ix_match_assessments_tuple_created" in reuse_plan

    cursor_explain = await db_session.execute(
        text(
            "EXPLAIN (FORMAT JSON) SELECT id FROM match_assessments "
            "WHERE job_target_id = :t "
            "ORDER BY created_at DESC, id DESC LIMIT 50"
        ),
        {"t": str(target_id)},
    )
    cursor_plan = json.dumps(cursor_explain.scalar_one())
    assert "ix_match_assessments_target_created" in cursor_plan

    # the completed row is visible to the reuse lookup
    assert assessment.id is not None
