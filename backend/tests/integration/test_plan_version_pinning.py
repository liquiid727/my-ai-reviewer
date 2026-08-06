"""RIP-014 version-pinned plan bridge — DB half (#112, §6.2/§7.2/§7.3/§10)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy import update as sqlalchemy_update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.plan_service import PlanService
from backend.domain.job_search_plan.enums import PlanStatus
from backend.domain.job_search_plan.policies import PlanDomainError, PlanVersionTupleError
from backend.domain.job_search_plan.schemas import PlanCreateRequest
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    JobDescriptionModel,
    JobDescriptionVersionModel,
    JobSearchPlanModel,
    JobTargetModel,
    MatchAssessmentModel,
    ResumeModel,
    ResumeVersionModel,
)
from backend.tests.conftest import TestSessionFactory, requires_db

pytestmark = requires_db


@pytest.fixture(autouse=True)
def _verified_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plan create/regenerate require an active verified LLM config; stub it."""

    async def verified_config(_: AsyncSession) -> object:
        return object()

    monkeypatch.setattr("backend.application.plan_service.get_active_verified_config", verified_config)
    monkeypatch.setattr(
        "backend.application.plan_regeneration_service.get_active_verified_config",
        verified_config,
    )


async def _seed_bridge(session: AsyncSession) -> dict[str, uuid.UUID]:
    """JD + versions + target + completed assessment for one coherent tuple."""
    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Backend Engineer",
        company="Example Co",
        raw_text="Build Python APIs.",
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
            ],
            "responsibilities": [{"key": "res-1", "value": "设计服务", "evidence": "服务设计"}],
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
    session.add(
        CandidateProfileModel(
            id=uuid.uuid4(),
            resume_id=resume.id,
            identity={"name": "Test Candidate"},
            skills=[{"name": "Go", "evidence": "Go 项目经验"}],
            ability_tags=["backend"],
        )
    )
    await session.flush()
    resume_version = ResumeVersionModel(
        id=uuid.uuid4(),
        source_type="parsed_resume",
        resume_id=resume.id,
        source_revision=1,
        content_hash="b" * 64,
        masked_snapshot={"masked_text": "[MASKED]"},
        profile_snapshot={
            "skills": [{"name": "Go", "evidence": "Go 项目经验 4 年", "confidence": 0.9}],
            "title": "资深后端工程师",
        },
        evidence_catalog=[{"key": "f-1", "value": "Go", "evidence": {"source_text": "Go 项目"}}],
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
    await session.flush()
    assessment = MatchAssessmentModel(
        id=uuid.uuid4(),
        job_target_id=target.id,
        jd_version_id=jd_version.id,
        resume_version_id=resume_version.id,
        status="completed",
        policy_version="match-v1",
        run_id=uuid.uuid4(),
        attempt=1,
        retryable=False,
        total_score=80,
    )
    session.add(assessment)
    await session.commit()
    return {
        "jd_id": jd.id,
        "resume_id": resume.id,
        "jd_version_id": jd_version.id,
        "resume_version_id": resume_version.id,
        "target_id": target.id,
        "assessment_id": assessment.id,
    }


async def _request(ids: dict[str, uuid.UUID]) -> PlanCreateRequest:
    return PlanCreateRequest(
        jd_id=ids["jd_id"],
        resume_id=ids["resume_id"],
        job_target_id=ids["target_id"],
        jd_version_id=ids["jd_version_id"],
        resume_version_id=ids["resume_version_id"],
        match_assessment_id=ids["assessment_id"],
    )


async def _request_with_assessment(
    ids: dict[str, uuid.UUID],
    match_assessment_id: uuid.UUID,
) -> PlanCreateRequest:
    return PlanCreateRequest(
        jd_id=ids["jd_id"],
        resume_id=ids["resume_id"],
        job_target_id=ids["target_id"],
        jd_version_id=ids["jd_version_id"],
        resume_version_id=ids["resume_version_id"],
        match_assessment_id=match_assessment_id,
    )


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


async def test_versioned_create_persists_full_tuple(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.tasks import plan_tasks

    monkeypatch.setattr(plan_tasks, "process_plan_generation", lambda *_a, **_k: None)
    ids = await _seed_bridge(db_session)
    async with TestSessionFactory() as session:
        plan = await PlanService().create(session, await _request(ids))
    assert plan.status == PlanStatus.GENERATING.value
    assert plan.job_target_id == ids["target_id"]
    assert plan.jd_version_id == ids["jd_version_id"]
    assert plan.resume_version_id == ids["resume_version_id"]
    assert plan.match_assessment_id == ids["assessment_id"]

    row = (
        await db_session.execute(select(JobSearchPlanModel).where(JobSearchPlanModel.id == plan.id))
    ).scalar_one()
    assert row.jd_version_id == ids["jd_version_id"]


async def test_versioned_create_rejects_unfinished_assessment(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.tasks import plan_tasks

    monkeypatch.setattr(plan_tasks, "process_plan_generation", lambda *_a, **_k: None)
    ids = await _seed_bridge(db_session)
    pending = await _insert_assessment(
        db_session,
        target_id=ids["target_id"],
        jd_version_id=ids["jd_version_id"],
        resume_version_id=ids["resume_version_id"],
        status="queued",
    )
    request = await _request_with_assessment(ids, pending.id)
    async with TestSessionFactory() as session:
        with pytest.raises(PlanVersionTupleError) as excinfo:
            await PlanService().create(session, request)
    assert excinfo.value.kind == "assessment"


async def test_versioned_create_rejects_partial_refs(
    db_session: AsyncSession,
) -> None:
    ids = await _seed_bridge(db_session)
    with pytest.raises(PlanDomainError) as excinfo:
        async with TestSessionFactory() as session:
            await PlanService().create(
                session,
                PlanCreateRequest(
                    jd_id=ids["jd_id"],
                    resume_id=ids["resume_id"],
                    job_target_id=ids["target_id"],
                ),
            )
    assert excinfo.value.code == 1001


async def test_versioned_create_rejects_cross_target_assessment(
    db_session: AsyncSession,
) -> None:
    ids = await _seed_bridge(db_session)
    other_jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Other JD",
        company="Other Co",
        raw_text="Other",
        status="ready",
        processing_step="done",
    )
    db_session.add(other_jd)
    await db_session.flush()
    other_jd_version = JobDescriptionVersionModel(
        id=uuid.uuid4(),
        job_description_id=other_jd.id,
        version_no=1,
        normalized_text="JD",
        structured={},
        evidence={},
        source_metadata={},
        content_hash="c" * 64,
        parser_version="legacy",
        schema_version="jd-v1",
        publication_reason="legacy_backfill",
    )
    other_resume = ResumeModel(id=uuid.uuid4(), status="evaluated", masked_text="[MASKED]")
    db_session.add(other_resume)
    await db_session.flush()
    other_resume_version = ResumeVersionModel(
        id=uuid.uuid4(),
        source_type="parsed_resume",
        resume_id=other_resume.id,
        source_revision=1,
        content_hash="d" * 64,
        masked_snapshot={},
        profile_snapshot={},
        evidence_catalog=[],
        parser_version="resume-parser-v3",
        schema_version="resume-v1",
        privacy_policy_version="resume-privacy-v1",
    )
    db_session.add_all([other_jd_version, other_resume_version])
    await db_session.flush()
    other_target = JobTargetModel(
        id=uuid.uuid4(),
        job_description_id=other_jd.id,
        default_jd_version_id=other_jd_version.id,
        default_resume_version_id=other_resume_version.id,
        revision=1,
    )
    db_session.add(other_target)
    await db_session.flush()
    other_assessment = await _insert_assessment(
        db_session,
        target_id=other_target.id,
        jd_version_id=other_jd_version.id,
        resume_version_id=other_resume_version.id,
        status="completed",
    )
    request = await _request_with_assessment(ids, other_assessment.id)
    with pytest.raises(PlanVersionTupleError) as excinfo:
        async with TestSessionFactory() as session:
            await PlanService().create(session, request)
    assert excinfo.value.kind == "assessment"


async def test_versioned_create_rejects_version_owned_by_other_jd(
    db_session: AsyncSession,
) -> None:
    ids = await _seed_bridge(db_session)
    other_jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Other JD",
        company="Other Co",
        raw_text="Other",
        status="ready",
        processing_step="done",
    )
    db_session.add(other_jd)
    await db_session.flush()
    foreign_jd_version = JobDescriptionVersionModel(
        id=uuid.uuid4(),
        job_description_id=other_jd.id,
        version_no=1,
        normalized_text="JD",
        structured={},
        evidence={},
        source_metadata={},
        content_hash="e" * 64,
        parser_version="legacy",
        schema_version="jd-v1",
        publication_reason="legacy_backfill",
    )
    db_session.add(foreign_jd_version)
    await db_session.commit()
    request = PlanCreateRequest(
        jd_id=ids["jd_id"],
        resume_id=ids["resume_id"],
        job_target_id=ids["target_id"],
        jd_version_id=foreign_jd_version.id,
        resume_version_id=ids["resume_version_id"],
        match_assessment_id=ids["assessment_id"],
    )
    with pytest.raises(PlanVersionTupleError) as excinfo:
        async with TestSessionFactory() as session:
            await PlanService().create(session, request)
    assert excinfo.value.kind == "scope"


async def test_versioned_duplicate_unfinished_is_rejected(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.tasks import plan_tasks

    monkeypatch.setattr(plan_tasks, "process_plan_generation", lambda *_a, **_k: None)
    ids = await _seed_bridge(db_session)
    async with TestSessionFactory() as session:
        await PlanService().create(session, await _request(ids))
    async with TestSessionFactory() as session:
        with pytest.raises(PlanDomainError) as excinfo:
            await PlanService().create(session, await _request(ids))
    assert excinfo.value.code == 1006


async def test_legacy_create_keeps_null_refs_and_input_contract(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    async_client: AsyncClient,
) -> None:
    from backend.tasks import plan_tasks

    monkeypatch.setattr(plan_tasks, "process_plan_generation", lambda *_a, **_k: None)
    ids = await _seed_bridge(db_session)
    async with TestSessionFactory() as session:
        plan = await PlanService().create(
            session,
            PlanCreateRequest(jd_id=ids["jd_id"], resume_id=ids["resume_id"]),
        )
    assert plan.job_target_id is None
    assert plan.jd_version_id is None
    assert plan.resume_version_id is None
    assert plan.match_assessment_id is None

    response = await async_client.get(f"/api/v1/plans/{plan.id}")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["input_contract"] == "legacy"
    assert payload["job_target_id"] is None


async def test_regeneration_retains_original_versions(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.application.plan_regeneration_service import PlanRegenerationService
    from backend.tasks import plan_tasks

    monkeypatch.setattr(plan_tasks, "process_plan_generation", lambda *_a, **_k: None)
    ids = await _seed_bridge(db_session)
    async with TestSessionFactory() as session:
        plan = await PlanService().create(session, await _request(ids))
    # Regeneration only applies to active plans; move the created row there.
    await db_session.execute(
        sqlalchemy_update(JobSearchPlanModel)
        .where(JobSearchPlanModel.id == plan.id)
        .values(status=PlanStatus.ACTIVE.value)
    )
    await db_session.commit()

    async def regenerate() -> JobSearchPlanModel:
        async with TestSessionFactory() as session:
            service = PlanRegenerationService()
            regenerated = await service.start(
                session,
                plan_id=plan.id,
                expected_revision=plan.revision,
            )
            await service.dispatch(session, regenerated)
            return regenerated

    regenerated = await regenerate()
    assert regenerated.status == PlanStatus.REGENERATING.value
    assert regenerated.job_target_id == ids["target_id"]
    assert regenerated.jd_version_id == ids["jd_version_id"]
    assert regenerated.resume_version_id == ids["resume_version_id"]
    assert regenerated.match_assessment_id == ids["assessment_id"]


async def test_versioned_generation_persists_snapshot_catalog_and_null_match_ref(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The versioned prepare -> persist path never writes an assessment UUID
    into the legacy jd_match_results FK column, and the persisted snapshot
    carries the deterministic version-built catalog."""
    from backend.application import plan_service as plan_service_module
    from backend.domain.job_search_plan.enums import PlanTaskCategory, PlanTaskPriority
    from backend.domain.job_search_plan.schemas import GeneratedPlanTask, PlanGenerationOutput

    ids = await _seed_bridge(db_session)
    async with TestSessionFactory() as session:
        plan = await PlanService().create(session, await _request(ids))

    async def fake_generate(_session, catalog, *, target_date, weekly_hours):
        first_requirement = next(
            entry for entry in catalog if entry.id.startswith("jd:") and ":requirement:" in entry.id
        )
        return (
            PlanGenerationOutput(
                suggested_title="版本固定计划",
                tasks=[
                    GeneratedPlanTask(
                        title=f"任务 {index}",
                        category=PlanTaskCategory.GAP_PRIORITY,
                        description="提升 Go 技能",
                        priority=PlanTaskPriority.HIGH,
                        due_offset_days=index * 2,
                        basis_ids=[first_requirement.id],
                    )
                    for index in range(1, 7)
                ],
            ),
            "verified-test-model",
        )

    monkeypatch.setattr(plan_service_module, "generate_plan_output", fake_generate)
    assert plan.generation_run_id is not None
    async with TestSessionFactory() as session:
        prepared = await PlanService().prepare_generation(session, plan_id=plan.id, run_id=plan.generation_run_id)
    assert prepared is not None
    assert prepared.match_result_id is None
    snapshot_catalog = prepared.input_snapshot["catalog"]
    assert isinstance(snapshot_catalog, list)
    assert any("jd:" in entry["id"] and ":requirement:" in entry["id"] for entry in snapshot_catalog)

    async with TestSessionFactory() as session:
        assert await PlanService().persist_initial(session, prepared) is True
    row = (
        await db_session.execute(select(JobSearchPlanModel).where(JobSearchPlanModel.id == plan.id))
    ).scalar_one()
    assert row.status == PlanStatus.ACTIVE.value
    assert row.match_result_id is None
    assert row.match_assessment_id == ids["assessment_id"]
    persisted = (
        await db_session.execute(
            select(JobSearchPlanModel.input_snapshot).where(JobSearchPlanModel.id == plan.id)
        )
    ).scalar_one()
    assert any("jd:" in entry["id"] for entry in persisted["catalog"])


async def test_versioned_detail_reports_input_contract(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    async_client: AsyncClient,
) -> None:
    from backend.tasks import plan_tasks

    monkeypatch.setattr(plan_tasks, "process_plan_generation", lambda *_a, **_k: None)
    ids = await _seed_bridge(db_session)
    async with TestSessionFactory() as session:
        plan = await PlanService().create(session, await _request(ids))

    response = await async_client.get(f"/api/v1/plans/{plan.id}")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["input_contract"] == "versioned"
    assert payload["job_target_id"] == str(ids["target_id"])
    assert payload["jd_version_id"] == str(ids["jd_version_id"])
    assert payload["resume_version_id"] == str(ids["resume_version_id"])
    assert payload["match_assessment_id"] == str(ids["assessment_id"])
    # Response never embeds complete JD/resume snapshots.
    assert "snapshot" not in response.text
