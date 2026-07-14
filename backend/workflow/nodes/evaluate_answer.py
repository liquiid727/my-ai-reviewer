"""evaluate_answer 节点 —— 调用 LLM 评估候选人回答并持久化结果。"""

import logging
import uuid

from backend.agents.evaluation_agent import AnswerEvaluationAgent
from backend.infrastructure.db.database import async_session_factory
from backend.infrastructure.db.models import QuestionAnswerModel
from backend.infrastructure.llm.gateway import LLMGateway
from backend.workflow.state import AnswerRecord, InterviewState

logger = logging.getLogger(__name__)


async def evaluate_answer(state: InterviewState) -> dict:
    """评估回答，保存到 DB，返回评分结果。"""
    idx = state["current_question_index"]
    question = state["questions"][idx]
    answer_text = state["_current_answer_text"]
    is_followup = state.get("pending_followup") is not None
    round_num = state["current_followup_count"] if is_followup else 0

    previous_answers = [a for a in state["answers"] if a["question_id"] == question["question_id"]]

    gateway = LLMGateway.from_settings()
    agent = AnswerEvaluationAgent(gateway)

    result = await agent.evaluate(
        question_text=question["question_text"],
        expected_points=question["expected_points"],
        answer_text=answer_text,
        followup_round=round_num,
        previous_answers=[dict(a) for a in previous_answers] if previous_answers else None,
    )

    question_id = uuid.UUID(question["question_id"])
    async with async_session_factory() as session:
        answer_model = QuestionAnswerModel(
            question_id=question_id,
            answer_text=answer_text,
            is_followup=is_followup,
            followup_round=round_num,
            followup_question=state.get("pending_followup"),
            score=result.score,
            feedback=result.feedback,
            key_points_hit=result.key_points_hit,
            key_points_missed=result.key_points_missed,
            weight=result.weight,
            needs_followup=result.needs_followup,
            raw_llm_response=result.model_dump(),
        )
        session.add(answer_model)
        await session.commit()

    answer_record = AnswerRecord(
        question_id=question["question_id"],
        answer_text=answer_text,
        is_followup=is_followup,
        followup_round=round_num,
        score=result.score,
        feedback=result.feedback,
        key_points_hit=result.key_points_hit,
        key_points_missed=result.key_points_missed,
        weight=result.weight,
        needs_followup=result.needs_followup,
    )

    logger.info(
        "Evaluated answer for question %s: score=%s, needs_followup=%s",
        question["question_id"],
        result.score,
        result.needs_followup,
    )

    return {
        "answers": [*state["answers"], answer_record],
        "_evaluation": result.model_dump(),
    }
