"""JD library and job-search plan persistence/API regression coverage."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.jd_service.processing import JDProcessingError, JDProcessingService
from backend.application.plan_regeneration_service import PlanRegenerationService
from backend.application.plan_service import PlanService, PreparedPlanGeneration, get_fresh_match
from backend.application.plan_task_service import PlanTaskService
from backend.domain.jd.policies import content_hash
from backend.domain.jd.schemas import ExtractedSkill, JDExtraction
from backend.domain.job_search_plan.enums import PlanTaskStatus
from backend.domain.job_search_plan.policies import PlanDomainError
from backend.domain.job_search_plan.schemas import PlanTaskPatchRequest
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    JDMatchResultModel,
    JobDescriptionModel,
    JobSearchPlanModel,
    JobSearchPlanTaskModel,
    ResumeModel,
    UserModel,
)
from backend.tests.conftest import requires_db


async def _seed_resume(session: AsyncSession) -> ResumeModel:
    resume = ResumeModel(
        id=uuid.uuid4(),
        status="evaluated",
        raw_text="Candidate has Python experience.",
        parsed_result={"profile": {"name": "Test Candidate"}},
    )
    session.add(resume)
    session.add(
        CandidateProfileModel(
            id=uuid.uuid4(),
            resume_id=resume.id,
            identity={"name": "Test Candidate", "email": "private@example.test"},
            skills=[{"name": "Python", "evidence": "Built APIs"}],
            ability_tags=["backend"],
        )
    )
    await session.commit()
    return resume


async def _seed_ready_jd(session: AsyncSession, *, title: str = "Backend Engineer") -> JobDescriptionModel:
    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title=title,
        company="Example Co",
        raw_text="Build Python APIs and operate services.",
        source_type="text",
        status="ready",
        processing_step="done",
        seniority="senior",
        responsibilities=["Build APIs"],
        required_skills=[{"name": "Python", "critical": True, "evidence": "Python APIs"}],
        preferred_skills=[{"name": "Kubernetes", "critical": False}],
        field_sources={"title": "llm", "required_skills": "llm"},
    )
    session.add(jd)
    await session.commit()
    await session.refresh(jd)
    return jd


async def _seed_match(
    session: AsyncSession,
    *,
    resume: ResumeModel,
    jd: JobDescriptionModel,
) -> JDMatchResultModel:
    match = JDMatchResultModel(
        id=uuid.uuid4(),
        jd_id=jd.id,
        resume_id=resume.id,
        match_score=75,
        skill_match=[],
        missing_skills=[],
        risk=[],
        gap=[],
        recommendation="conditional",
    )
    session.add(match)
    await session.commit()
    await session.refresh(match)
    return match


@requires_db
async def test_jd_list_detail_patch_and_legacy_match(async_client: AsyncClient, db_session: AsyncSession) -> None:
    resume = await _seed_resume(db_session)
    jd = await _seed_ready_jd(db_session)
    resume_id = str(resume.id)
    jd_id = str(jd.id)

    listing = await async_client.get("/api/v1/jd", params={"status": "ready", "page": 1, "page_size": 1})
    assert listing.status_code == 200
    body = listing.json()
    assert body["code"] == 0
    assert body["data"]["total"] >= 1
    assert "raw_text" not in body["data"]["items"][0]

    detail = await async_client.get(f"/api/v1/jd/{jd_id}")
    detail_body = detail.json()
    assert detail_body["code"] == 0
    assert detail_body["data"]["raw_text"] == jd.raw_text

    patched = await async_client.patch(
        f"/api/v1/jd/{jd_id}",
        json={
            "expected_updated_at": detail_body["data"]["updated_at"],
            "title": "Principal Backend Engineer",
            "required_skills": [],
        },
    )
    patched_body = patched.json()
    assert patched_body["code"] == 0
    assert patched_body["data"]["title"] == "Principal Backend Engineer"
    assert patched_body["data"]["required_skills"] == []
    assert patched_body["data"]["field_sources"]["title"] == "manual"

    conflict = await async_client.patch(
        f"/api/v1/jd/{jd_id}",
        json={"expected_updated_at": detail_body["data"]["updated_at"], "company": "Other Co"},
    )
    assert conflict.json()["code"] == 1003

    legacy = await async_client.post(
        "/api/v1/jd",
        json={
            "title": "Platform Engineer",
            "company": "Example Co",
            "raw_text": "Build resilient Python services.",
            "required_skills": ["Python"],
        },
    )
    legacy_body = legacy.json()
    assert legacy_body["code"] == 0
    assert legacy_body["data"]["status"] == "ready"

    matched = await async_client.post(
        "/api/v1/jd/match",
        json={"jd_id": jd_id, "resume_id": resume_id},
    )
    assert matched.json()["code"] == 0


@requires_db
async def test_plan_reference_protects_jd_delete_and_list_detail_are_persistent(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    resume = await _seed_resume(db_session)
    jd = await _seed_ready_jd(db_session, title="Data Engineer")
    plan = JobSearchPlanModel(
        id=uuid.uuid4(),
        jd_id=jd.id,
        resume_id=resume.id,
        title="Data Engineer plan",
        status="active",
        revision=3,
    )
    db_session.add(plan)
    db_session.add(
        JobSearchPlanTaskModel(
            id=uuid.uuid4(),
            plan_id=plan.id,
            title="Update resume",
            category="resume",
            description="Highlight Python data work",
            source="ai",
            priority="high",
            status="todo",
            sort_order=0,
        )
    )
    await db_session.commit()

    protected = await async_client.delete(f"/api/v1/jd/{jd.id}")
    assert protected.json()["code"] == 1005

    listing = await async_client.get("/api/v1/plans", params={"q": "Data Engineer"})
    listing_body = listing.json()
    assert listing_body["code"] == 0
    row = next(item for item in listing_body["data"]["items"] if item["id"] == str(plan.id))
    assert row["progress"] == {"done": 0, "total": 1, "percent": 0}
    assert row["next_due_task"] == "Update resume"

    detail = await async_client.get(f"/api/v1/plans/{plan.id}")
    detail_body = detail.json()
    assert detail_body["code"] == 0
    assert detail_body["data"]["revision"] == 3
    assert len(detail_body["data"]["tasks"]) == 1


@requires_db
async def test_plan_task_revision_progress_and_delete_rules(db_session: AsyncSession) -> None:
    resume = await _seed_resume(db_session)
    jd = await _seed_ready_jd(db_session, title="ML Engineer")
    plan = JobSearchPlanModel(
        id=uuid.uuid4(),
        jd_id=jd.id,
        resume_id=resume.id,
        title="ML Engineer plan",
        status="active",
        revision=0,
    )
    task = JobSearchPlanTaskModel(
        id=uuid.uuid4(),
        plan_id=plan.id,
        title="Prepare portfolio evidence",
        category="evidence_project",
        description="",
        source="manual",
        priority="medium",
        status="todo",
        sort_order=0,
    )
    db_session.add_all([plan, task])
    await db_session.commit()

    service = PlanTaskService()
    completed_plan, _, progress = await service.patch(
        db_session,
        plan_id=plan.id,
        task_id=task.id,
        payload=PlanTaskPatchRequest(expected_revision=0, status=PlanTaskStatus.DONE),
    )
    assert progress.model_dump() == {"done": 1, "total": 1, "percent": 100}
    assert completed_plan.status == "completed"
    assert completed_plan.revision == 1

    with pytest.raises(PlanDomainError, match="Reopen"):
        await service.delete(db_session, plan_id=plan.id, task_id=task.id, expected_revision=1)

    reopened_plan, _, progress = await service.patch(
        db_session,
        plan_id=plan.id,
        task_id=task.id,
        payload=PlanTaskPatchRequest(expected_revision=1, status=PlanTaskStatus.TODO),
    )
    assert progress.model_dump() == {"done": 0, "total": 1, "percent": 0}
    assert reopened_plan.status == "active"
    assert reopened_plan.revision == 2

    with pytest.raises(PlanDomainError) as conflict:
        await service.patch(
            db_session,
            plan_id=plan.id,
            task_id=task.id,
            payload=PlanTaskPatchRequest(expected_revision=1, title="Stale write"),
        )
    assert conflict.value.code == 1007


@requires_db
async def test_jd_worker_stale_run_and_duplicate_lookup_are_conditional(db_session: AsyncSession) -> None:
    user = UserModel(
        id=uuid.uuid4(),
        username=f"jd-worker-{uuid.uuid4()}",
        email=f"jd-worker-{uuid.uuid4()}@example.test",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    raw_text = "Build resilient Python services for a distributed platform."
    digest = content_hash(raw_text)
    first = JobDescriptionModel(
        id=uuid.uuid4(),
        user_id=user.id,
        raw_text=raw_text,
        source_type="text",
        status="ready",
        processing_step="done",
        content_hash=digest,
    )
    second = JobDescriptionModel(
        id=uuid.uuid4(),
        user_id=user.id,
        raw_text=raw_text,
        source_type="text",
        status="ready",
        processing_step="done",
        content_hash=digest,
    )
    current_run = uuid.uuid4()
    target = JobDescriptionModel(
        id=uuid.uuid4(),
        user_id=user.id,
        raw_text=raw_text,
        source_type="text",
        status="processing",
        processing_step="duplicate_check",
        processing_run_id=current_run,
    )
    db_session.add_all([first, second, target])
    await db_session.commit()

    service = JDProcessingService()
    duplicate_state = await service.duplicate_check(db_session, target.id, current_run)
    assert duplicate_state == "duplicate_pending"
    await db_session.refresh(target)
    assert target.duplicate_of_id in {first.id, second.id}

    wrote = await service._write_current(
        db_session,
        target.id,
        uuid.uuid4(),
        {"status": "failed", "processing_error": "stale worker"},
    )
    assert wrote is False
    await db_session.refresh(target)
    assert target.status == "duplicate_pending"
    assert target.processing_error is None


@requires_db
async def test_legacy_jd_failures_keep_their_compatibility_codes(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    missing = str(uuid.uuid4())
    resume = await _seed_resume(db_session)

    missing_jd = await async_client.get(f"/api/v1/jd/{missing}")
    missing_match = await async_client.get(f"/api/v1/jd/match/{missing}")
    missing_resume = await async_client.post("/api/v1/jd/match", json={"resume_id": missing})
    invalid_match = await async_client.post("/api/v1/jd/match", json={"resume_id": str(resume.id)})

    assert missing_jd.json()["code"] == 404
    assert missing_match.json()["code"] == 404
    assert missing_resume.json()["code"] == 404
    assert invalid_match.json()["code"] == 400


@requires_db
async def test_jd_import_broker_failure_persists_a_safe_failed_state(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def llm_ready(_: AsyncSession) -> bool:
        return True

    def broker_failure(*_: object) -> None:
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr("backend.api.v1.jd.has_verified_config", llm_ready)
    monkeypatch.setattr("backend.tasks.jd_tasks.process_jd_pipeline", broker_failure)

    response = await async_client.post(
        "/api/v1/jd/import/text",
        json={"raw_text": "Build resilient Python APIs for distributed systems."},
    )
    body = response.json()
    assert body["code"] == 5004
    assert body["data"]["status"] == "failed"
    assert body["data"]["processing_error"] == "Unable to dispatch JD processing. Please retry."


@requires_db
async def test_jd_processing_state_machine_preserves_manual_fields_and_safe_failures(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid.uuid4()
    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        title="Manual platform role",
        raw_text="Build resilient Python services for a distributed platform and operate production systems.",
        source_type="text",
        status="processing",
        processing_step="queued",
        processing_run_id=run_id,
        field_sources={"title": "manual"},
    )
    db_session.add(jd)
    await db_session.commit()

    class Extractor:
        def __init__(self, _: object) -> None:
            pass

        async def extract(self, _: str) -> JDExtraction:
            return JDExtraction(
                title="LLM title must not replace manual title",
                company="Example Co",
                location="Shanghai",
                seniority=None,
                responsibilities=["Build APIs"],
                required_skills=[ExtractedSkill(name="Python", evidence="Python services")],
                preferred_skills=[ExtractedSkill(name="Kubernetes", evidence="Container platform")],
            )

    gateway_configs: list[object] = []

    async def verified_config(_: AsyncSession) -> object:
        return object()

    def gateway_from_config(config: object) -> object:
        gateway_configs.append(config)
        return object()

    monkeypatch.setattr("backend.application.jd_service.processing.get_active_verified_config", verified_config)
    monkeypatch.setattr("backend.application.jd_service.processing.LLMGateway.from_config", gateway_from_config)
    monkeypatch.setattr("backend.application.jd_service.processing.JDExtractor", Extractor)

    service = JDProcessingService()
    assert await service.source_extract(db_session, jd.id, run_id) == "processing"
    assert await service.duplicate_check(db_session, jd.id, run_id) == "processing"
    assert await service.llm_extract(db_session, jd.id, run_id) == "ready"
    await db_session.refresh(jd)
    assert jd.status == "ready"
    assert jd.processing_step == "done"
    assert jd.title == "Manual platform role"
    assert jd.company == "Example Co"
    assert jd.seniority is None
    assert jd.field_sources["title"] == "manual"
    assert jd.field_sources["company"] == "llm"
    assert len(gateway_configs) == 1

    failed_run = uuid.uuid4()
    jd.status = "processing"
    jd.processing_step = "llm_extract"
    jd.processing_run_id = failed_run
    await db_session.commit()
    await service.mark_failed(
        db_session,
        jd.id,
        failed_run,
        "llm_extract",
        JDProcessingError("JD structured extraction failed", 5001),
    )
    await db_session.refresh(jd)
    assert jd.status == "failed"
    assert jd.processing_error == "JD structured extraction failed"


@requires_db
async def test_fresh_match_reuses_then_refreshes_after_profile_change(db_session: AsyncSession) -> None:
    resume = await _seed_resume(db_session)
    jd = await _seed_ready_jd(db_session)

    _profile, first = await get_fresh_match(db_session, jd=jd, resume_id=resume.id)
    await db_session.commit()
    _profile, reused = await get_fresh_match(db_session, jd=jd, resume_id=resume.id)
    assert reused.id == first.id

    profile = (
        await db_session.execute(select(CandidateProfileModel).where(CandidateProfileModel.resume_id == resume.id))
    ).scalar_one()
    profile.updated_at = datetime.now(UTC) + timedelta(seconds=1)
    await db_session.commit()

    _profile, refreshed = await get_fresh_match(db_session, jd=jd, resume_id=resume.id)
    assert refreshed.id != first.id


@requires_db
async def test_plan_dispatch_failure_retries_with_latest_revision(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume = await _seed_resume(db_session)
    jd = await _seed_ready_jd(db_session)

    async def verified_config(_: AsyncSession) -> object:
        return object()

    def broker_failure(*_: object) -> None:
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr("backend.application.plan_service.get_active_verified_config", verified_config)
    monkeypatch.setattr("backend.tasks.plan_tasks.process_plan_generation", broker_failure)

    created = await async_client.post(
        "/api/v1/plans",
        json={"jd_id": str(jd.id), "resume_id": str(resume.id)},
    )
    created_body = created.json()
    assert created_body["code"] == 5004
    assert created_body["data"]["status"] == "failed"
    assert created_body["data"]["revision"] == 1

    retried = await async_client.post(
        f"/api/v1/plans/{created_body['data']['id']}/retry",
        json={"expected_revision": created_body["data"]["revision"]},
    )
    retried_body = retried.json()
    assert retried_body["code"] == 5004
    assert retried_body["data"]["status"] == "failed"
    assert retried_body["data"]["revision"] == 3

    stale_retry = await async_client.post(
        f"/api/v1/plans/{created_body['data']['id']}/retry",
        json={"expected_revision": 1},
    )
    assert stale_retry.json()["code"] == 1007


@requires_db
async def test_plan_create_duplicate_and_eligible_resume_contract(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume = await _seed_resume(db_session)
    jd = await _seed_ready_jd(db_session)

    async def verified_config(_: AsyncSession) -> object:
        return object()

    monkeypatch.setattr("backend.application.plan_service.get_active_verified_config", verified_config)
    monkeypatch.setattr("backend.tasks.plan_tasks.process_plan_generation", lambda *_: None)

    eligible = await async_client.get("/api/v1/resume", params={"has_profile": "true", "page_size": 100})
    eligible_rows = eligible.json()["data"]["items"]
    eligible_row = next(row for row in eligible_rows if row["id"] == str(resume.id))
    assert set(eligible_row) <= {"id", "display_name", "updated_at"}

    created = await async_client.post(
        "/api/v1/plans",
        json={"jd_id": str(jd.id), "resume_id": str(resume.id)},
    )
    created_body = created.json()
    assert created_body["code"] == 0
    assert created_body["data"]["status"] == "generating"

    duplicate = await async_client.post(
        "/api/v1/plans",
        json={"jd_id": str(jd.id), "resume_id": str(resume.id)},
    )
    duplicate_body = duplicate.json()
    assert duplicate_body["code"] == 1006
    assert duplicate_body["data"]["plan_id"] == created_body["data"]["id"]


@requires_db
async def test_initial_plan_persistence_rejects_stale_workers(db_session: AsyncSession) -> None:
    resume = await _seed_resume(db_session)
    jd = await _seed_ready_jd(db_session)
    match = await _seed_match(db_session, resume=resume, jd=jd)
    run_id = uuid.uuid4()
    plan = JobSearchPlanModel(
        id=uuid.uuid4(),
        jd_id=jd.id,
        resume_id=resume.id,
        title="Initial generation",
        status="generating",
        generation_run_id=run_id,
        revision=0,
    )
    plan_id = plan.id
    db_session.add(plan)
    await db_session.commit()
    prepared = PreparedPlanGeneration(
        plan_id=plan_id,
        run_id=run_id,
        match_result_id=match.id,
        input_snapshot={"catalog": []},
        model_name="verified-test-model",
        tasks=[
            {
                "title": "Generated first task",
                "category": "gap_priority",
                "description": "Address the most important gap",
                "basis": [],
                "source": "ai",
                "priority": "high",
                "status": "todo",
                "due_date": date(2026, 8, 15),
                "sort_order": 0,
            }
        ],
    )

    service = PlanService()
    assert await service.persist_initial(db_session, prepared) is True
    await db_session.refresh(plan)
    assert plan.status == "active"
    assert plan.revision == 1
    tasks = (
        (await db_session.execute(select(JobSearchPlanTaskModel).where(JobSearchPlanTaskModel.plan_id == plan_id)))
        .scalars()
        .all()
    )
    assert [task.title for task in tasks] == ["Generated first task"]

    stale = PreparedPlanGeneration(
        plan_id=plan_id,
        run_id=uuid.uuid4(),
        match_result_id=match.id,
        input_snapshot={"catalog": []},
        model_name="verified-test-model",
        tasks=prepared.tasks,
    )
    assert await service.persist_initial(db_session, stale) is False
    unchanged = (
        (await db_session.execute(select(JobSearchPlanTaskModel).where(JobSearchPlanTaskModel.plan_id == plan_id)))
        .scalars()
        .all()
    )
    assert [task.title for task in unchanged] == ["Generated first task"]


@requires_db
async def test_plan_failure_and_regeneration_preserve_current_work(db_session: AsyncSession) -> None:
    resume = await _seed_resume(db_session)
    jd = await _seed_ready_jd(db_session)
    match = await _seed_match(db_session, resume=resume, jd=jd)
    run_id = uuid.uuid4()
    plan = JobSearchPlanModel(
        id=uuid.uuid4(),
        jd_id=jd.id,
        resume_id=resume.id,
        title="Preserve work",
        status="regenerating",
        previous_status="active",
        generation_run_id=run_id,
        revision=4,
    )
    manual = JobSearchPlanTaskModel(
        id=uuid.uuid4(),
        plan_id=plan.id,
        title="Manual portfolio note",
        category="evidence_project",
        description="Keep this user task",
        source="manual",
        priority="medium",
        status="todo",
        sort_order=0,
    )
    completed_ai = JobSearchPlanTaskModel(
        id=uuid.uuid4(),
        plan_id=plan.id,
        title="Completed AI task",
        category="resume",
        description="Keep this completed task",
        source="ai",
        priority="high",
        status="done",
        sort_order=1,
    )
    replaceable_ai = JobSearchPlanTaskModel(
        id=uuid.uuid4(),
        plan_id=plan.id,
        title="Replace this AI task",
        category="skill",
        description="Old AI task",
        source="ai",
        priority="medium",
        status="todo",
        sort_order=2,
    )
    db_session.add_all([plan, manual, completed_ai, replaceable_ai])
    await db_session.commit()

    prepared = PreparedPlanGeneration(
        plan_id=plan.id,
        run_id=run_id,
        match_result_id=match.id,
        input_snapshot={"catalog": []},
        model_name="verified-test-model",
        tasks=[
            {
                "title": "New AI task",
                "category": "skill",
                "description": "Generated replacement",
                "basis": [],
                "source": "ai",
                "priority": "medium",
                "status": "todo",
                "due_date": date(2026, 8, 20),
                "sort_order": 0,
            }
        ],
    )
    assert await PlanRegenerationService().persist(db_session, prepared) is True
    rows = (
        (
            await db_session.execute(
                select(JobSearchPlanTaskModel)
                .where(JobSearchPlanTaskModel.plan_id == plan.id)
                .order_by(JobSearchPlanTaskModel.sort_order)
            )
        )
        .scalars()
        .all()
    )
    assert {row.title for row in rows} == {"Manual portfolio note", "Completed AI task", "New AI task"}
    assert all(row.title != "Replace this AI task" for row in rows)

    await db_session.refresh(plan)
    plan.status = "regenerating"
    plan.previous_status = "active"
    plan.generation_run_id = uuid.uuid4()
    plan.generation_error = None
    before = [(row.id, row.title, row.status, row.source, row.sort_order) for row in rows]
    await db_session.commit()
    await PlanRegenerationService().mark_failed(
        db_session,
        plan_id=plan.id,
        run_id=plan.generation_run_id,
        error=PlanDomainError("Plan regeneration failed", 5001),
    )
    await db_session.refresh(plan)
    after = (
        (
            await db_session.execute(
                select(JobSearchPlanTaskModel)
                .where(JobSearchPlanTaskModel.plan_id == plan.id)
                .order_by(JobSearchPlanTaskModel.sort_order)
            )
        )
        .scalars()
        .all()
    )
    assert plan.status == "active"
    assert plan.generation_error == "Plan regeneration failed"
    assert [(row.id, row.title, row.status, row.source, row.sort_order) for row in after] == before
