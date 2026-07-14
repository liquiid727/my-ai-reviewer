"""面试异步任务 —— Celery 报告生成任务。"""

import asyncio
import logging
import uuid

from backend.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="generate_interview_report")
def generate_report_task(interview_id: str) -> dict:
    """异步生成面试报告（Celery task 入口，内部调用 async 实现）。"""
    return asyncio.run(_generate_report(interview_id))


async def _generate_report(interview_id: str) -> dict:
    """面试报告生成的异步实现。"""
    from sqlalchemy import select, update

    from backend.agents.report_agent import ReportGenerationAgent
    from backend.domain.interview.enums import InterviewStatus
    from backend.infrastructure.db.database import async_session_factory
    from backend.infrastructure.db.models import (
        InterviewModel,
        InterviewQuestionModel,
        InterviewReportModel,
        QuestionAnswerModel,
    )
    from backend.infrastructure.llm.gateway import LLMGateway

    iid = uuid.UUID(interview_id)

    async with async_session_factory() as session:
        result = await session.execute(select(InterviewModel).where(InterviewModel.id == iid))
        interview = result.scalar_one_or_none()
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")

        q_result = await session.execute(
            select(InterviewQuestionModel)
            .where(InterviewQuestionModel.interview_id == iid)
            .order_by(InterviewQuestionModel.sequence_num)
        )
        questions = list(q_result.scalars().all())

        interview_data: dict = {
            "jd_text": interview.jd_text or "",
            "questions": [],
        }

        for q in questions:
            a_result = await session.execute(
                select(QuestionAnswerModel)
                .where(QuestionAnswerModel.question_id == q.id)
                .order_by(QuestionAnswerModel.followup_round)
            )
            answers = list(a_result.scalars().all())

            q_data = {
                "sequence_num": q.sequence_num,
                "question_text": q.question_text,
                "stage": q.stage,
                "difficulty": q.difficulty,
                "expected_points": q.expected_points,
                "answers": [
                    {
                        "answer_text": a.answer_text,
                        "is_followup": a.is_followup,
                        "followup_round": a.followup_round,
                        "followup_question": a.followup_question,
                        "score": a.score,
                        "feedback": a.feedback,
                        "key_points_hit": a.key_points_hit,
                        "key_points_missed": a.key_points_missed,
                        "weight": a.weight,
                    }
                    for a in answers
                ],
            }
            interview_data["questions"].append(q_data)

    try:
        gateway = LLMGateway.from_settings()
        agent = ReportGenerationAgent(gateway)
        report = await agent.generate(interview_data)

        async with async_session_factory() as session:
            report_model = InterviewReportModel(
                interview_id=iid,
                overall_score=report.overall_score,
                dimension_scores=[d.model_dump() for d in report.dimension_scores],
                per_question_summary=[q.model_dump() for q in report.per_question_summary],
                strengths=[s.model_dump() for s in report.strengths],
                weaknesses=[w.model_dump() for w in report.weaknesses],
                recommendation=report.recommendation,
                summary=report.summary,
                llm_model=agent.model_info,
            )
            session.add(report_model)

            await session.execute(
                update(InterviewModel).where(InterviewModel.id == iid).values(status=InterviewStatus.COMPLETED.value)
            )
            await session.commit()

        logger.info("Report generated for interview %s", interview_id)
        return {"status": "completed", "interview_id": interview_id}

    except Exception:
        logger.exception("Failed to generate report for interview %s", interview_id)
        async with async_session_factory() as session:
            await session.execute(
                update(InterviewModel).where(InterviewModel.id == iid).values(status=InterviewStatus.FAILED.value)
            )
            await session.commit()
        raise
