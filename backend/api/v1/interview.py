"""面试相关 API 端点 —— 创建面试、启动、提交回答、查询状态/报告/列表。"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.schemas import APIResponse
from backend.application.interview_service import InterviewService
from backend.infrastructure.db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interview", tags=["interview"])


# ── Request Schemas ──


class CreateInterviewReq(BaseModel):
    """创建面试请求。"""

    resume_id: uuid.UUID
    jd_text: str | None = None
    question_count: int = Field(default=5, ge=3, le=10)


class SubmitAnswerReq(BaseModel):
    """提交回答请求。"""

    question_id: uuid.UUID
    answer_text: str = Field(min_length=10, max_length=10000)


# ── Response Schemas ──


class InterviewCreatedData(BaseModel):
    """创建面试响应。"""

    interview_id: str
    status: str


class QuestionPresentData(BaseModel):
    """题目展示数据。"""

    question_id: str
    question_text: str
    stage: str
    difficulty: str
    current_num: int
    total_count: int
    is_followup: bool = False
    followup_round: int = 0


class AnswerResultData(BaseModel):
    """回答评分结果。"""

    score: float
    feedback: str
    key_points_hit: list[str]
    key_points_missed: list[str]
    next: QuestionPresentData | None = None
    is_finished: bool


class InterviewStatusData(BaseModel):
    """面试状态数据。"""

    interview_id: str
    status: str
    current_question_num: int | None
    total_questions: int | None
    answered_count: int


class InterviewReportData(BaseModel):
    """面试报告数据。"""

    interview_id: str
    overall_score: float
    dimension_scores: list[dict]
    per_question_summary: list[dict]
    strengths: list[dict]
    weaknesses: list[dict]
    recommendation: str
    summary: str | None
    llm_model: str | None
    created_at: datetime


class InterviewListItem(BaseModel):
    """面试列表条目。"""

    interview_id: str
    resume_id: str
    status: str
    question_count: int
    overall_score: float | None = None
    recommendation: str | None = None
    created_at: datetime


# ── Helpers ──


def _extract_interrupt_value(state: object) -> dict | None:
    """安全提取 LangGraph interrupt 值，无中断时返回 None。"""
    tasks = getattr(state, "tasks", None)
    if not tasks:
        return None
    first_task = tasks[0]
    interrupts = getattr(first_task, "interrupts", None)
    if not interrupts:
        return None
    return interrupts[0].value


def _build_question_data(interrupt_value: dict) -> QuestionPresentData:
    """从 interrupt 值中构建题目展示数据。"""
    question_data = interrupt_value.get("question", {})
    is_followup = interrupt_value.get("type") == "followup"
    return QuestionPresentData(
        question_id=question_data.get("question_id", ""),
        question_text=(
            interrupt_value.get("followup_question", "") if is_followup else question_data.get("question_text", "")
        ),
        stage=question_data.get("stage", ""),
        difficulty=question_data.get("difficulty", ""),
        current_num=interrupt_value.get("current_num", 1),
        total_count=interrupt_value.get("total_count", 0),
        is_followup=is_followup,
        followup_round=interrupt_value.get("followup_round", 0),
    )


def _build_eval_response(last_eval: dict) -> dict:
    """从最后一条评估记录中提取响应字段。"""
    return {
        "score": last_eval.get("score", 0),
        "feedback": last_eval.get("feedback", ""),
        "key_points_hit": last_eval.get("key_points_hit", []),
        "key_points_missed": last_eval.get("key_points_missed", []),
    }


# ── Endpoints ──


@router.post("/create")
async def create_interview(
    req: CreateInterviewReq,
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """创建面试会话。"""
    service = InterviewService(db)
    try:
        interview = await service.create_interview(
            resume_id=req.resume_id,
            jd_text=req.jd_text,
            question_count=req.question_count,
        )
    except ValueError as e:
        error_code = str(e)
        if error_code == "RESUME_NOT_FOUND":
            return APIResponse(code=1001, message="Resume not found")
        if error_code == "RESUME_NOT_READY":
            return APIResponse(code=1002, message="Resume not ready for interview")
        raise

    return APIResponse(
        data=InterviewCreatedData(
            interview_id=str(interview.id),
            status=interview.status,
        )
    )


@router.post("/{interview_id}/start")
async def start_interview(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """开始面试：生成题目并返回第一题。"""
    from backend.workflow.graphs.interview_graph import get_compiled_graph

    service = InterviewService(db)
    try:
        interview = await service.validate_for_start(interview_id)
    except ValueError as e:
        error_code = str(e)
        if error_code == "INTERVIEW_NOT_FOUND":
            return APIResponse(code=1003, message="Interview not found")
        if error_code == "INTERVIEW_NOT_PENDING":
            return APIResponse(code=1004, message="Interview is not in pending status")
        raise

    graph = await get_compiled_graph()
    thread_id = interview.graph_thread_id or str(interview_id)
    config = {"configurable": {"thread_id": thread_id}}

    try:
        await graph.ainvoke(
            {
                "interview_id": str(interview_id),
                "resume_id": str(interview.resume_id),
                "jd_text": interview.jd_text or "",
                "question_count": interview.question_count,
                "questions": [],
                "current_question_index": 0,
                "answers": [],
                "current_followup_count": 0,
                "pending_followup": None,
                "is_finished": False,
                "_current_answer_text": "",
                "_evaluation": {},
            },
            config=config,
        )
    except Exception:
        logger.exception("Failed to start interview %s", interview_id)
        await service.mark_failed(interview_id, "Graph execution failed during start")
        return APIResponse(code=1010, message="Failed to start interview, please try again")

    state = await graph.aget_state(config)
    interrupt_value = _extract_interrupt_value(state)

    if not interrupt_value:
        logger.error("No interrupt produced after starting interview %s", interview_id)
        await service.mark_failed(interview_id, "No interrupt produced after graph start")
        return APIResponse(code=1010, message="Failed to start interview, please try again")

    return APIResponse(data=_build_question_data(interrupt_value))


@router.post("/{interview_id}/answer")
async def submit_answer(
    interview_id: uuid.UUID,
    req: SubmitAnswerReq,
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """提交回答：评分并返回下一题或结束。"""
    from langgraph.types import Command

    from backend.workflow.graphs.interview_graph import get_compiled_graph

    service = InterviewService(db)
    try:
        interview = await service.validate_for_answer(interview_id)
    except ValueError as e:
        error_code = str(e)
        if error_code == "INTERVIEW_NOT_FOUND":
            return APIResponse(code=1003, message="Interview not found")
        if error_code == "INTERVIEW_NOT_IN_PROGRESS":
            return APIResponse(code=1005, message="Interview is not in progress")
        raise

    graph = await get_compiled_graph()
    thread_id = interview.graph_thread_id or str(interview_id)
    config = {"configurable": {"thread_id": thread_id}}

    try:
        await graph.ainvoke(Command(resume=req.answer_text), config=config)
    except Exception:
        logger.exception("Failed to process answer for interview %s", interview_id)
        return APIResponse(code=1011, message="Failed to process answer, please try again")

    state = await graph.aget_state(config)
    state_values = state.values

    last_answers = state_values.get("answers", [])
    if not last_answers:
        logger.error("No answer records found after evaluation for interview %s", interview_id)
        return APIResponse(code=1011, message="Evaluation failed, no answer recorded")

    last_eval = last_answers[-1]
    eval_data = _build_eval_response(last_eval)

    if state_values.get("is_finished"):
        return APIResponse(
            data=AnswerResultData(
                **eval_data,
                next=None,
                is_finished=True,
            )
        )

    interrupt_value = _extract_interrupt_value(state)
    if not interrupt_value:
        logger.error("No interrupt after answer for interview %s", interview_id)
        return APIResponse(code=1011, message="Failed to get next question")

    return APIResponse(
        data=AnswerResultData(
            **eval_data,
            next=_build_question_data(interrupt_value),
            is_finished=False,
        )
    )


@router.get("/{interview_id}/status")
async def get_interview_status(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """查询面试状态。"""
    service = InterviewService(db)
    try:
        status_data = await service.get_interview_status(interview_id)
    except ValueError as e:
        if str(e) == "INTERVIEW_NOT_FOUND":
            return APIResponse(code=1003, message="Interview not found")
        raise

    return APIResponse(data=InterviewStatusData(**status_data))


@router.get("/{interview_id}/report")
async def get_interview_report(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取面试报告。"""
    service = InterviewService(db)

    try:
        is_generating = await service.is_report_generating(interview_id)
    except ValueError:
        return APIResponse(code=1003, message="Interview not found")

    if is_generating:
        return APIResponse(code=2001, message="Report is being generated, please try again later")

    report = await service.get_report(interview_id)
    if not report:
        return APIResponse(code=1006, message="Report not found")

    return APIResponse(
        data=InterviewReportData(
            interview_id=str(interview_id),
            overall_score=report.overall_score,
            dimension_scores=report.dimension_scores,
            per_question_summary=report.per_question_summary,
            strengths=report.strengths,
            weaknesses=report.weaknesses,
            recommendation=report.recommendation,
            summary=report.summary,
            llm_model=report.llm_model,
            created_at=report.created_at,
        )
    )


@router.get("/list")
async def list_interviews(
    resume_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """面试列表。"""
    service = InterviewService(db)
    items = await service.list_interviews(resume_id=resume_id)
    return APIResponse(data=[InterviewListItem(**item) for item in items])
