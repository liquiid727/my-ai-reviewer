import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.interview.enums import InterviewStatus
from backend.infrastructure.db.models import (
    InterviewModel,
    InterviewQuestionModel,
    InterviewReportModel,
    QuestionAnswerModel,
)
from tests.conftest import requires_db

pytestmark = requires_db


@pytest_asyncio.fixture
async def sample_interview(db_session: AsyncSession, sample_resume):
    interview = InterviewModel(
        id=uuid.uuid4(),
        resume_id=sample_resume.id,
        jd_text="Python backend developer position",
        status=InterviewStatus.PENDING.value,
        question_count=5,
        graph_thread_id=str(uuid.uuid4()),
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)
    return interview


@pytest_asyncio.fixture
async def in_progress_interview(db_session: AsyncSession, sample_resume):
    interview = InterviewModel(
        id=uuid.uuid4(),
        resume_id=sample_resume.id,
        status=InterviewStatus.IN_PROGRESS.value,
        question_count=3,
        graph_thread_id=str(uuid.uuid4()),
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)
    return interview


@pytest_asyncio.fixture
async def completed_interview_with_report(db_session: AsyncSession, sample_resume):
    interview = InterviewModel(
        id=uuid.uuid4(),
        resume_id=sample_resume.id,
        status=InterviewStatus.COMPLETED.value,
        question_count=3,
        graph_thread_id=str(uuid.uuid4()),
    )
    db_session.add(interview)
    await db_session.flush()

    question = InterviewQuestionModel(
        id=uuid.uuid4(),
        interview_id=interview.id,
        sequence_num=1,
        question_text="Describe Python async programming",
        stage="basic",
        difficulty="medium",
        expected_points=["asyncio", "event loop"],
    )
    db_session.add(question)
    await db_session.flush()

    answer = QuestionAnswerModel(
        id=uuid.uuid4(),
        question_id=question.id,
        answer_text="Python uses asyncio for async programming...",
        score=80,
        feedback="Good understanding",
        key_points_hit=["asyncio"],
        key_points_missed=["event loop details"],
        weight=1.0,
    )
    db_session.add(answer)

    report = InterviewReportModel(
        id=uuid.uuid4(),
        interview_id=interview.id,
        overall_score=78.5,
        dimension_scores=[
            {"name": "技术能力", "score": 80, "reason": "Good"},
            {"name": "项目深度", "score": 75, "reason": "Average"},
        ],
        per_question_summary=[
            {"question_num": 1, "question_text": "Q1", "final_score": 80, "summary": "Well answered"},
        ],
        strengths=[{"point": "Strong Python skills", "evidence": "Detailed asyncio explanation"}],
        weaknesses=[{"point": "Limited scope", "evidence": "No project examples"}],
        recommendation="yes",
        summary="Good candidate overall",
        llm_model="gpt-4o",
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(interview)
    return interview


class TestCreateInterview:
    @pytest.mark.asyncio
    async def test_create_success(self, async_client: AsyncClient, sample_resume):
        resp = await async_client.post(
            "/api/v1/interview/create",
            json={
                "resume_id": str(sample_resume.id),
                "jd_text": "Python backend developer",
                "question_count": 5,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["status"] == "pending"
        assert data["data"]["interview_id"]

    @pytest.mark.asyncio
    async def test_create_without_jd(self, async_client: AsyncClient, sample_resume):
        resp = await async_client.post(
            "/api/v1/interview/create",
            json={"resume_id": str(sample_resume.id), "question_count": 5},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    @pytest.mark.asyncio
    async def test_create_resume_not_found(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await async_client.post(
            "/api/v1/interview/create",
            json={"resume_id": fake_id, "question_count": 5},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 1001

    @pytest.mark.asyncio
    async def test_create_resume_not_ready(self, async_client: AsyncClient, db_session: AsyncSession):
        from backend.infrastructure.db.models import ResumeModel

        resume = ResumeModel(
            id=uuid.uuid4(),
            status="parsing",
            raw_text="processing...",
        )
        db_session.add(resume)
        await db_session.commit()

        resp = await async_client.post(
            "/api/v1/interview/create",
            json={"resume_id": str(resume.id), "question_count": 5},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 1002

    @pytest.mark.asyncio
    async def test_create_question_count_validation(self, async_client: AsyncClient, sample_resume):
        resp = await async_client.post(
            "/api/v1/interview/create",
            json={"resume_id": str(sample_resume.id), "question_count": 1},
        )
        assert resp.status_code == 422

        resp = await async_client.post(
            "/api/v1/interview/create",
            json={"resume_id": str(sample_resume.id), "question_count": 20},
        )
        assert resp.status_code == 422


class TestGetInterviewStatus:
    @pytest.mark.asyncio
    async def test_status_success(self, async_client: AsyncClient, sample_interview):
        resp = await async_client.get(f"/api/v1/interview/{sample_interview.id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["status"] == "pending"
        assert data["data"]["interview_id"] == str(sample_interview.id)

    @pytest.mark.asyncio
    async def test_status_not_found(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await async_client.get(f"/api/v1/interview/{fake_id}/status")
        assert resp.status_code == 200
        assert resp.json()["code"] == 1003


class TestGetInterviewReport:
    @pytest.mark.asyncio
    async def test_report_success(self, async_client: AsyncClient, completed_interview_with_report):
        iv = completed_interview_with_report
        resp = await async_client.get(f"/api/v1/interview/{iv.id}/report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["overall_score"] == 78.5
        assert data["data"]["recommendation"] == "yes"
        assert len(data["data"]["dimension_scores"]) == 2
        assert len(data["data"]["strengths"]) == 1

    @pytest.mark.asyncio
    async def test_report_not_found(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await async_client.get(f"/api/v1/interview/{fake_id}/report")
        assert resp.status_code == 200
        assert resp.json()["code"] == 1003

    @pytest.mark.asyncio
    async def test_report_generating(self, async_client: AsyncClient, db_session: AsyncSession, sample_resume):
        interview = InterviewModel(
            id=uuid.uuid4(),
            resume_id=sample_resume.id,
            status=InterviewStatus.REPORT_GENERATING.value,
            question_count=3,
        )
        db_session.add(interview)
        await db_session.commit()

        resp = await async_client.get(f"/api/v1/interview/{interview.id}/report")
        assert resp.status_code == 200
        assert resp.json()["code"] == 2001

    @pytest.mark.asyncio
    async def test_report_interview_exists_but_no_report(
        self,
        async_client: AsyncClient,
        sample_interview,
    ):
        resp = await async_client.get(f"/api/v1/interview/{sample_interview.id}/report")
        assert resp.status_code == 200
        assert resp.json()["code"] == 1006


class TestListInterviews:
    @pytest.mark.asyncio
    async def test_list_all(self, async_client: AsyncClient, sample_interview):
        resp = await async_client.get("/api/v1/interview/list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1

    @pytest.mark.asyncio
    async def test_list_by_resume_id(self, async_client: AsyncClient, sample_interview, sample_resume):
        resp = await async_client.get(f"/api/v1/interview/list?resume_id={sample_resume.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        for item in data["data"]:
            assert item["resume_id"] == str(sample_resume.id)

    @pytest.mark.asyncio
    async def test_list_empty_for_unknown_resume(self, async_client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await async_client.get(f"/api/v1/interview/list?resume_id={fake_id}")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    @pytest.mark.asyncio
    async def test_list_includes_report_data(
        self,
        async_client: AsyncClient,
        completed_interview_with_report,
    ):
        iv = completed_interview_with_report
        resp = await async_client.get(f"/api/v1/interview/list?resume_id={iv.resume_id}")
        assert resp.status_code == 200
        items = resp.json()["data"]
        completed = [i for i in items if i["interview_id"] == str(iv.id)]
        assert len(completed) == 1
        assert completed[0]["overall_score"] == 78.5
        assert completed[0]["recommendation"] == "yes"
