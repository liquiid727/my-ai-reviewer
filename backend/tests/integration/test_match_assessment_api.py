"""Match Assessment API + worker integration tests (RIP-013 #110, §7, §9).

Covers idempotent create/reuse/force, active-duplicate 409, retry with a new
run id on the same row, stale-run worker exit without a result write, and
low-score eligibility (a completed low-score assessment is returned as a
normal completed result). The broker dispatch is monkeypatched to fail so the
broker-failure diagnostic path is deterministic; worker evaluation runs
through MatchAssessmentWorker with a deterministic fake semantic matcher.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import backend.tasks.match_tasks as match_tasks_module
from backend.application.match_assessment import MatchAssessmentWorker
from backend.infrastructure.db.models import (
    JobDescriptionModel,
    JobDescriptionVersionModel,
    MatchAssessmentModel,
    ResumeModel,
    ResumeVersionModel,
)
from backend.infrastructure.matchers import (
    ALLOWED_DIMENSIONS,
    ConstrainedSemanticMatcher,
    MatchedDimension,
    MatchedGap,
    MatchSemanticResult,
)
from backend.tests.conftest import requires_db

pytestmark = requires_db

# Force the broker-failure path deterministically: the dispatch helper raises,
# and the create command persists a safe retryable diagnostic instead.


def _broker_down(*_args: object, **_kwargs: object) -> None:
    raise ConnectionError("broker unreachable")


match_tasks_module.process_match_assessment = _broker_down  # type: ignore[assignment]


async def _seed(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Return (jd_version_id, resume_version_id, target_id)."""
    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Match JD",
        raw_text="JD",
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
            "skills": [{"name": "Go", "evidence": "Go 项目经验 4 年", "confidence": 0.9}]
        },
        evidence_catalog=[],
        parser_version="resume-parser-v3",
        schema_version="resume-v1",
        privacy_policy_version="resume-privacy-v1",
    )
    session.add_all([jd_version, resume_version])
    await session.flush()
    from backend.infrastructure.db.models import JobTargetModel

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
    run_id: uuid.UUID | None = None,
    attempt: int = 1,
) -> MatchAssessmentModel:
    assessment = MatchAssessmentModel(
        id=uuid.uuid4(),
        job_target_id=target_id,
        jd_version_id=jd_version_id,
        resume_version_id=resume_version_id,
        status=status,
        policy_version="match-v1",
        run_id=run_id or uuid.uuid4(),
        attempt=attempt,
        retryable=False,
    )
    session.add(assessment)
    await session.commit()
    await session.refresh(assessment)
    return assessment


class _FakeMatcher(ConstrainedSemanticMatcher):
    """Deterministic classifier: every dimension gets the given raw score."""

    def __init__(self, score: float = 80.0) -> None:
        super().__init__(gateway=object())  # type: ignore[arg-type]  # classify is overridden
        self.score = score

    async def classify(
        self,
        *,
        catalog: object,
        dimensions: list[str],
        requirements: list[str],
    ) -> MatchSemanticResult:
        dims = [
            MatchedDimension(
                key=key,
                raw_score=self.score,
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


async def _complete(
    session: AsyncSession,
    assessment: MatchAssessmentModel,
    *,
    score: float = 80.0,
) -> str:
    worker = MatchAssessmentWorker(
        session=session,
        matcher=_FakeMatcher(score=score),  # type: ignore[arg-type]
    )
    return await worker.evaluate(assessment.id, assessment.run_id)


async def test_create_persists_queued_then_broker_failure_is_safe_diagnostic(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    jd_version_id, resume_version_id, target_id = await _seed(db_session)
    response = await async_client.post(
        "/api/v1/match-assessments",
        json={
            "job_target_id": str(target_id),
            "jd_version_id": str(jd_version_id),
            "resume_version_id": str(resume_version_id),
            "policy_version": "match-v1",
            "force": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "failed"
    assert payload["error_code"] == "ASSESSMENT_DEPENDENCY_TIMEOUT"
    assert payload["retryable"] is True
    assert payload["attempt"] == 1
    assert payload["reused"] is False
    # the broker failure is a safe, retryable diagnostic on the same row
    rows = (
        await db_session.execute(
            select(MatchAssessmentModel).where(
                MatchAssessmentModel.id == uuid.UUID(payload["id"])
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == "failed"
    assert rows[0].retryable is True


async def test_create_reuses_completed_without_force(
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
    outcome = await _complete(db_session, assessment)
    assert outcome == "completed"

    response = await async_client.post(
        "/api/v1/match-assessments",
        json={
            "job_target_id": str(target_id),
            "jd_version_id": str(jd_version_id),
            "resume_version_id": str(resume_version_id),
        },
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] == str(assessment.id)
    assert payload["status"] == "completed"
    assert payload["reused"] is True
    assert payload["run_id"] == str(assessment.run_id)


async def test_create_force_new_row_after_completion(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    jd_version_id, resume_version_id, target_id = await _seed(db_session)
    first = await _insert_assessment(
        db_session,
        jd_version_id=jd_version_id,
        resume_version_id=resume_version_id,
        target_id=target_id,
        status="queued",
    )
    assert await _complete(db_session, first) == "completed"

    response = await async_client.post(
        "/api/v1/match-assessments",
        json={
            "job_target_id": str(target_id),
            "jd_version_id": str(jd_version_id),
            "resume_version_id": str(resume_version_id),
            "force": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] != str(first.id)
    assert payload["reused"] is False
    # the forced run hit the broker-failure path (dispatch is patched down)
    assert payload["status"] == "failed"
    assert payload["error_code"] == "ASSESSMENT_DEPENDENCY_TIMEOUT"


async def test_create_active_duplicate_conflict(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    jd_version_id, resume_version_id, target_id = await _seed(db_session)
    active = await _insert_assessment(
        db_session,
        jd_version_id=jd_version_id,
        resume_version_id=resume_version_id,
        target_id=target_id,
        status="queued",
    )
    response = await async_client.post(
        "/api/v1/match-assessments",
        json={
            "job_target_id": str(target_id),
            "jd_version_id": str(jd_version_id),
            "resume_version_id": str(resume_version_id),
            "force": True,  # force never bypasses an active duplicate
        },
    )
    assert response.status_code == 409
    assert str(active.id) in response.json()["detail"]


async def test_retry_failed_clears_diagnostic_and_requeues(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    jd_version_id, resume_version_id, target_id = await _seed(db_session)
    failed = await _insert_assessment(
        db_session,
        jd_version_id=jd_version_id,
        resume_version_id=resume_version_id,
        target_id=target_id,
        status="failed",
        run_id=uuid.uuid4(),
        attempt=2,
    )
    failed.error_code = "ASSESSMENT_FAILED"
    failed.error_details = "safe diagnostic"
    failed.retryable = False
    await db_session.commit()

    response = await async_client.post(f"/api/v1/match-assessments/{failed.id}/retry")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] == str(failed.id)
    assert payload["status"] == "failed"
    assert payload["attempt"] == 3
    assert payload["error_code"] == "ASSESSMENT_DEPENDENCY_TIMEOUT"
    assert payload["retryable"] is True

    rows = (
        await db_session.execute(
            select(MatchAssessmentModel).where(
                MatchAssessmentModel.id == failed.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].attempt == 3
    # retry cleared the old diagnostic, then the patched broker failed the run
    assert rows[0].error_code == "ASSESSMENT_DEPENDENCY_TIMEOUT"


async def test_stale_worker_exits_without_result_write(
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
    assert await _complete(db_session, assessment) == "completed"

    # the same run_id is no longer the current run: the worker must exit
    # without rewriting anything (a completed result is immutable)
    stale = await MatchAssessmentWorker(session=db_session, matcher=_FakeMatcher(score=99.0)).evaluate(  # type: ignore[arg-type]
        assessment.id, assessment.run_id
    )
    assert stale == "stale"
    rows = (
        await db_session.execute(
            select(MatchAssessmentModel).where(
                MatchAssessmentModel.id == assessment.id
            )
        )
    ).scalars().all()
    assert rows[0].status == "completed"
    assert float(rows[0].total_score) == 80.0
    assert rows[0].model_name == "fake-model"


async def test_worker_completes_with_immutable_result(
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
    outcome = await _complete(db_session, assessment, score=72.0)
    assert outcome == "completed"

    rows = (
        await db_session.execute(
            select(MatchAssessmentModel).where(
                MatchAssessmentModel.id == assessment.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == "completed"
    assert float(rows[0].total_score) == 72.0
    assert rows[0].score_before_caps is not None
    assert rows[0].recommendation == "hire"
    assert rows[0].overall_confidence is not None
    assert rows[0].model_name == "fake-model"
    assert rows[0].schema_version == "match-v1-result"
    assert rows[0].completed_at is not None
    assert len(rows[0].dimension_scores) == 8
    assert len(rows[0].gaps) == 1
    assert rows[0].evidence_summary["jd_evidence"] == 1


async def test_low_score_still_returns_completed_result(
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
    assert await _complete(db_session, assessment, score=20.0) == "completed"

    response = await async_client.get(f"/api/v1/match-assessments/{assessment.id}")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "completed"
    result = payload["result"]
    assert result["total_score"] == 20.0
    assert result["recommendation"] == "reject"
    # recommendation bands are advisory; a low score is still a completed result
    assert result["dimension_scores"][0]["key"] == "required_skills"


async def test_list_cursor_and_detail(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    jd_version_id, resume_version_id, target_id = await _seed(db_session)
    first = await _insert_assessment(
        db_session,
        jd_version_id=jd_version_id,
        resume_version_id=resume_version_id,
        target_id=target_id,
        status="failed",
    )
    second = await _insert_assessment(
        db_session,
        jd_version_id=jd_version_id,
        resume_version_id=resume_version_id,
        target_id=target_id,
        status="queued",
    )

    response = await async_client.get(
        "/api/v1/match-assessments",
        params={"job_target_id": str(target_id), "limit": 1},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["assessments"]) == 1
    assert data["next_before_id"] == str(second.id)

    page2 = await async_client.get(
        "/api/v1/match-assessments",
        params={
            "job_target_id": str(target_id),
            "before_created_at": data["next_before_created_at"],
            "before_id": data["next_before_id"],
        },
    )
    assert page2.status_code == 200
    page2_data = page2.json()["data"]
    assert [a["id"] for a in page2_data["assessments"]] == [str(first.id)]
    assert page2_data["next_before_id"] is None

    detail = await async_client.get(f"/api/v1/match-assessments/{first.id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["status"] == "failed"
    assert detail.json()["data"]["result"] is None

    missing = await async_client.get(
        f"/api/v1/match-assessments/{uuid.uuid4()}"
    )
    assert missing.status_code == 404
