"""generate_questions 节点 —— 调用 LLM 生成面试题目并持久化到数据库。"""

import logging
import uuid

from sqlalchemy import update

from backend.agents.question_agent import QuestionGenerationAgent
from backend.domain.interview.enums import InterviewStatus
from backend.infrastructure.db.database import async_session_factory
from backend.infrastructure.db.models import InterviewModel, InterviewQuestionModel
from backend.infrastructure.llm.gateway import LLMGateway
from backend.workflow.state import InterviewState, QuestionItem

logger = logging.getLogger(__name__)


async def generate_questions(state: InterviewState) -> dict:
    """LLM 生成题目，写入 DB，更新面试状态为 in_progress。"""
    gateway = LLMGateway.from_settings()
    agent = QuestionGenerationAgent(gateway)

    output = await agent.generate(
        resume_data=state["resume_data"],
        jd_text=state["jd_text"],
        count=state["question_count"],
    )

    interview_id = uuid.UUID(state["interview_id"])
    question_items: list[QuestionItem] = []

    async with async_session_factory() as session:
        for idx, q in enumerate(output.questions):
            model = InterviewQuestionModel(
                interview_id=interview_id,
                sequence_num=idx + 1,
                question_text=q.question_text,
                stage=q.stage,
                difficulty=q.difficulty,
                expected_points=q.expected_points,
                jd_relevance=q.jd_relevance,
            )
            session.add(model)
            await session.flush()

            question_items.append(
                QuestionItem(
                    question_id=str(model.id),
                    question_text=q.question_text,
                    stage=q.stage,
                    difficulty=q.difficulty,
                    expected_points=q.expected_points,
                    jd_relevance=q.jd_relevance,
                )
            )

        await session.execute(
            update(InterviewModel)
            .where(InterviewModel.id == interview_id)
            .values(status=InterviewStatus.IN_PROGRESS.value)
        )
        await session.commit()

    logger.info("Generated %d questions for interview %s", len(question_items), interview_id)

    return {
        "questions": question_items,
        "current_question_index": 0,
        "current_followup_count": 0,
        "pending_followup": None,
    }
