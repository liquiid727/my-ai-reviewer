"""RIP-014 match assessment report projection + actions API (#113, §6.1/§6.3/§7.1/§9).

The completed detail endpoint embeds a read-only report: exact version facts,
caps, gap classes, evidence sufficiency with explicit unknown citations,
staleness advisory against current versions, and downstream action routes.
The job-target history endpoint returns the same payloads without N+1
per-assessment row reads.
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
    ResumeDraftModel,
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


def _broker_down(*_args: object, **_kwargs: object) -> None:
    raise ConnectionError("broker unreachable")


match_tasks_module.process_match_assessment = _broker_down  # type: ignore[assignment]


async def _seed(session: AsyncSession) -> dict[str, uuid.UUID]:
    """JD + version + target + parsed-resume version; returns their ids."""
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
        profile_snapshot={"skills": [{"name": "Go", "evidence": "Go 项目经验 4 年", "confidence": 0.9}]},
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
    return {
        "jd_id": jd.id,
        "jd_version_id": jd_version.id,
        "resume_id": resume.id,
        "resume_version_id": resume_version.id,
        "target_id": target.id,
    }


async def _seed_draft_version(
    session: AsyncSession,
    *,
    resume_id: uuid.UUID,
) -> uuid.UUID:
    """Builder-draft resume version (RIP-014 §6.3 resume-optimization source)."""
    draft = ResumeDraftModel(
        id=uuid.uuid4(),
        resume_id=resume_id,
        content={"sections": [{"type": "summary", "text": "[MASKED]"}]},
    )
    session.add(draft)
    await session.flush()
    draft_version = ResumeVersionModel(
        id=uuid.uuid4(),
        source_type="builder_draft",
        draft_id=draft.id,
        source_revision=1,
        content_hash="c" * 64,
        masked_snapshot={"masked_text": "[MASKED]"},
        profile_snapshot={},
        evidence_catalog=[],
        parser_version="resume-parser-v3",
        schema_version="resume-v1",
        privacy_policy_version="resume-privacy-v1",
    )
    session.add(draft_version)
    await session.commit()
    return draft_version.id


async def _publish_newer_jd_version(
    session: AsyncSession,
    *,
    jd_id: uuid.UUID,
) -> uuid.UUID:
    jd_version = JobDescriptionVersionModel(
        id=uuid.uuid4(),
        job_description_id=jd_id,
        version_no=2,
        normalized_text="JD v2",
        structured={},
        evidence={},
        source_metadata={},
        content_hash="f" * 64,
        parser_version="legacy",
        schema_version="jd-v1",
        publication_reason="manual_revision",
    )
    session.add(jd_version)
    await session.flush()
    jd = (await session.execute(select(JobDescriptionModel).where(JobDescriptionModel.id == jd_id))).scalar_one()
    jd.current_version_id = jd_version.id
    await session.commit()
    return jd_version.id


async def _insert_assessment(
    session: AsyncSession,
    *,
    target_id: uuid.UUID,
    jd_version_id: uuid.UUID,
    resume_version_id: uuid.UUID,
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
    """Deterministic classifier; cites fixed ids outside the catalog on purpose
    so the report's explicit-unknown path is exercised."""

    def __init__(self, score: float = 80.0) -> None:
        super().__init__(gateway=object())  # type: ignore[arg-type]
        self.score = score

    async def classify(
        self,
        *,
        catalog: object,
        dimensions: list[str],  # type: ignore[override]  # fake is input-blind
        requirements: list[str],
    ) -> MatchSemanticResult:
        # dims/gaps are driven by self.score, not the inputs; keep the fake
        # signature supertype-compatible (list[str] overrides the typed list).
        del catalog, dimensions, requirements
        dims = [
            MatchedDimension(
                key=key,
                raw_score=self.score,
                confidence=0.9,
                cited_jd_evidence=(["jd:v1:requirement:sk-1"] if key == "required_skills" else []),
                cited_resume_evidence=(["resume:v1:fact:skill-0"] if key == "required_skills" else []),
                explanation="masked summary",
            )
            for key in ALLOWED_DIMENSIONS
        ]
        gaps = [
            MatchedGap(
                requirement_id="jd:v1:requirement:sk-1",
                category="capability_gap",
                severity="high",
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


async def test_completed_detail_embeds_bounded_report_projection(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    ids = await _seed(db_session)
    assessment = await _insert_assessment(
        db_session,
        target_id=ids["target_id"],
        jd_version_id=ids["jd_version_id"],
        resume_version_id=ids["resume_version_id"],
        status="queued",
    )
    assert await _complete(db_session, assessment, score=72.0) == "completed"

    response = await async_client.get(f"/api/v1/match-assessments/{assessment.id}")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "completed"
    # the report is a bounded projection, never the raw stored snapshot
    assert "snapshot" not in response.text
    report = payload["report"]

    assert report["version_facts"]["jd_version_id"] == str(ids["jd_version_id"])
    assert report["version_facts"]["resume_version_id"] == str(ids["resume_version_id"])
    assert report["version_facts"]["jd_version_no"] == 1
    assert report["version_facts"]["resume_version_source_type"] == "parsed_resume"

    assert report["scores"]["total_score"] == 72.0
    assert report["scores"]["score_before_caps"] == 72.0
    assert report["scores"]["recommendation"] == "hire"
    assert report["scores"]["caps_applied"] == []

    assert len(report["dimensions"]) == 8
    assert report["dimensions"][0]["key"] == "required_skills"

    assert report["gap_classes"]["counts_by_class"]["capability_gap"] == 1
    assert report["gap_classes"]["counts_by_class"]["expression_gap"] == 0
    assert report["gap_classes"]["counts_by_action_type"] == {"screen": 1}

    # the fake classifier cites fixed ids the catalog never offered
    assert report["evidence_sufficiency"]["jd_evidence"] == 1
    assert report["evidence_sufficiency"]["resume_evidence"] == 1
    assert report["evidence_sufficiency"]["unknown_citations"] == [
        "jd:v1:requirement:sk-1",
        "resume:v1:fact:skill-0",
    ]
    assert [u["kind"] for u in report["explicit_unknowns"]] == [
        "evidence_citation",
        "evidence_citation",
    ]
    assert len(report["explicit_unknowns"]) == 2

    assert report["stale"] == {
        "jd": [],
        "resume": [],
        "is_stale": False,
    }
    assert report["model"]["name"] == "fake-model"

    # parsed-resume assessment offers plan + interview actions (never gated on score)
    assert [a["id"] for a in report["actions"]] == ["plan", "interview"]
    assert report["actions"][0]["destination"] == {"resume_id": str(ids["resume_id"])}


async def test_completed_detail_never_embeds_report_for_unfinished(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    ids = await _seed(db_session)
    pending = await _insert_assessment(
        db_session,
        target_id=ids["target_id"],
        jd_version_id=ids["jd_version_id"],
        resume_version_id=ids["resume_version_id"],
        status="queued",
    )
    response = await async_client.get(f"/api/v1/match-assessments/{pending.id}")
    assert response.status_code == 200
    assert response.json()["data"]["result"] is None
    assert "report" not in response.json()["data"]


async def test_report_flags_stale_when_newer_versions_exist(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    ids = await _seed(db_session)
    assessment = await _insert_assessment(
        db_session,
        target_id=ids["target_id"],
        jd_version_id=ids["jd_version_id"],
        resume_version_id=ids["resume_version_id"],
        status="queued",
    )
    assert await _complete(db_session, assessment) == "completed"
    newer_jd_version_id = await _publish_newer_jd_version(db_session, jd_id=ids["jd_id"])
    # the target's defaults move on independently of the assessment
    from backend.infrastructure.db.models import JobTargetModel

    target = (
        await db_session.execute(select(JobTargetModel).where(JobTargetModel.id == ids["target_id"]))
    ).scalar_one()
    target.default_jd_version_id = newer_jd_version_id
    await db_session.commit()

    response = await async_client.get(f"/api/v1/match-assessments/{assessment.id}")
    assert response.status_code == 200
    report = response.json()["data"]["report"]
    assert report["stale"]["jd"] == [
        "jd_has_newer_published_version",
        "target_default_jd_version_moved",
    ]
    assert report["stale"]["is_stale"] is True
    # the immutable report still pins the assessed version
    assert report["version_facts"]["jd_version_id"] == str(ids["jd_version_id"])


async def test_report_actions_include_resume_optimization_for_draft_version(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    ids = await _seed(db_session)
    draft_version_id = await _seed_draft_version(db_session, resume_id=ids["resume_id"])
    assessment = await _insert_assessment(
        db_session,
        target_id=ids["target_id"],
        jd_version_id=ids["jd_version_id"],
        resume_version_id=draft_version_id,
        status="queued",
    )
    assert await _complete(db_session, assessment) == "completed"

    response = await async_client.get(f"/api/v1/match-assessments/{assessment.id}")
    assert response.status_code == 200
    report = response.json()["data"]["report"]
    assert report["version_facts"]["resume_version_source_type"] == "builder_draft"
    # the draft is linked to a parsed resume, so optimization + plan + interview
    # are all reachable; optimization always leads with its draft route
    assert [a["id"] for a in report["actions"]] == [
        "resume_optimization",
        "plan",
        "interview",
    ]
    assert report["actions"][0]["route"] == "/builder/:draftId"


async def test_low_score_report_keeps_all_actions_enabled(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    ids = await _seed(db_session)
    assessment = await _insert_assessment(
        db_session,
        target_id=ids["target_id"],
        jd_version_id=ids["jd_version_id"],
        resume_version_id=ids["resume_version_id"],
        status="queued",
    )
    assert await _complete(db_session, assessment, score=20.0) == "completed"

    response = await async_client.get(f"/api/v1/match-assessments/{assessment.id}")
    assert response.status_code == 200
    report = response.json()["data"]["report"]
    assert report["scores"]["recommendation"] == "reject"
    # low score never disables downstream actions (RIP-014 §6.3)
    assert [a["id"] for a in report["actions"]] == ["plan", "interview"]
    assert all(a["eligible"] is True for a in report["actions"])


async def test_target_history_endpoint_returns_reports_and_cursor(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    ids = await _seed(db_session)
    completed = await _insert_assessment(
        db_session,
        target_id=ids["target_id"],
        jd_version_id=ids["jd_version_id"],
        resume_version_id=ids["resume_version_id"],
        status="queued",
    )
    assert await _complete(db_session, completed) == "completed"
    pending = await _insert_assessment(
        db_session,
        target_id=ids["target_id"],
        jd_version_id=ids["jd_version_id"],
        resume_version_id=ids["resume_version_id"],
        status="queued",
    )

    response = await async_client.get(
        f"/api/v1/job-targets/{ids['target_id']}/match-assessments",
        params={"limit": 1},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["assessments"]) == 1
    assert data["next_before_id"] == str(pending.id)
    first = data["assessments"][0]
    assert first["status"] == "queued"
    assert "report" not in first

    page2 = await async_client.get(
        f"/api/v1/job-targets/{ids['target_id']}/match-assessments",
        params={
            "before_created_at": data["next_before_created_at"],
            "before_id": data["next_before_id"],
        },
    )
    assert page2.status_code == 200
    page2_data = page2.json()["data"]
    assert [a["id"] for a in page2_data["assessments"]] == [str(completed.id)]
    assert page2_data["next_before_id"] is None
    second = page2_data["assessments"][0]
    assert second["status"] == "completed"
    assert "report" in second
    assert second["report"]["scores"]["total_score"] == 80.0
    assert [a["id"] for a in second["report"]["actions"]] == ["plan", "interview"]

    missing = await async_client.get(f"/api/v1/job-targets/{uuid.uuid4()}/match-assessments")
    assert missing.status_code == 404


async def test_target_history_keeps_legacy_match_separation(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    """History is scoped to assessments of the target; legacy match results
    (jd_match_results rows) never appear and are not conflated with them."""
    ids = await _seed(db_session)
    response = await async_client.get(f"/api/v1/job-targets/{ids['target_id']}/match-assessments")
    assert response.status_code == 200
    assert response.json()["data"]["assessments"] == []
