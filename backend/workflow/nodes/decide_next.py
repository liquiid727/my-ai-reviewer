"""decide_next 及辅助节点 —— 条件路由 + 追问生成 + 下一题 + 结束。"""

import logging

from sqlalchemy import update

from backend.agents.followup_agent import FollowupGenerationAgent
from backend.domain.interview.enums import InterviewStatus
from backend.infrastructure.db.database import async_session_factory
from backend.infrastructure.db.models import InterviewModel
from backend.infrastructure.llm.gateway import LLMGateway
from backend.tasks.interview_tasks import generate_report_task
from backend.workflow.state import InterviewState

logger = logging.getLogger(__name__)

MAX_FOLLOWUP_ROUNDS = 2


def decide_next(state: InterviewState) -> str:
    """条件路由：追问 / 下一题 / 结束。"""
    evaluation = state["_evaluation"]
    idx = state["current_question_index"]
    followup_count = state["current_followup_count"]

    if evaluation.get("needs_followup") and followup_count < MAX_FOLLOWUP_ROUNDS:
        return "generate_followup"
    elif idx + 1 < len(state["questions"]):
        return "next_question"
    else:
        return "finish"


async def generate_followup(state: InterviewState) -> dict:
    """调用 LLM 生成追问题目。"""
    idx = state["current_question_index"]
    question = state["questions"][idx]
    evaluation = state["_evaluation"]

    gateway = LLMGateway.from_settings()
    agent = FollowupGenerationAgent(gateway)

    last_answer = state["answers"][-1]
    result = await agent.generate(
        question_text=question["question_text"],
        answer_text=last_answer["answer_text"],
        score=last_answer["score"],
        feedback=last_answer["feedback"],
        key_points_missed=evaluation.get("key_points_missed", []),
        followup_reason=evaluation.get("followup_reason"),
    )

    logger.info("Generated followup for question %s", question["question_id"])

    return {
        "pending_followup": result.followup_question,
        "current_followup_count": state["current_followup_count"] + 1,
    }


def next_question(state: InterviewState) -> dict:
    """推进到下一题。"""
    return {
        "current_question_index": state["current_question_index"] + 1,
        "current_followup_count": 0,
        "pending_followup": None,
    }


async def finish_interview(state: InterviewState) -> dict:
    """面试结束，更新状态并触发 Celery 报告生成。"""
    import uuid

    interview_id = uuid.UUID(state["interview_id"])

    async with async_session_factory() as session:
        await session.execute(
            update(InterviewModel)
            .where(InterviewModel.id == interview_id)
            .values(status=InterviewStatus.REPORT_GENERATING.value)
        )
        await session.commit()

    generate_report_task.delay(state["interview_id"])
    logger.info("Interview %s finished, report generation triggered", state["interview_id"])

    return {"is_finished": True}
