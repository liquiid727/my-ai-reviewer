"""面试业务编排服务 —— 协调 LangGraph 图和数据库操作。"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.interview.enums import InterviewStatus
from backend.infrastructure.db.models import (
    InterviewModel,
    InterviewQuestionModel,
    InterviewReportModel,
    QuestionAnswerModel,
    ResumeModel,
)

logger = logging.getLogger(__name__)


class InterviewService:
    """面试服务：创建面试、启动面试流程、提交回答、查询状态/报告。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_interview(
        self,
        resume_id: uuid.UUID,
        jd_text: str | None = None,
        question_count: int = 5,
    ) -> InterviewModel:
        """创建面试会话，校验简历已评估。"""
        result = await self._session.execute(select(ResumeModel).where(ResumeModel.id == resume_id))
        resume = result.scalar_one_or_none()
        if not resume:
            raise ValueError("RESUME_NOT_FOUND")

        valid_statuses = {"evaluated", "classified"}
        if resume.status not in valid_statuses:
            raise ValueError("RESUME_NOT_READY")

        interview = InterviewModel(
            resume_id=resume_id,
            jd_text=jd_text,
            question_count=question_count,
            status=InterviewStatus.PENDING.value,
            graph_thread_id=str(uuid.uuid4()),
        )
        self._session.add(interview)
        await self._session.commit()
        await self._session.refresh(interview)

        logger.info("Created interview %s for resume %s", interview.id, resume_id)
        return interview

    async def get_interview(self, interview_id: uuid.UUID) -> InterviewModel | None:
        """获取面试会话。"""
        result = await self._session.execute(select(InterviewModel).where(InterviewModel.id == interview_id))
        return result.scalar_one_or_none()

    async def validate_for_start(self, interview_id: uuid.UUID) -> InterviewModel:
        """校验面试可以启动，返回面试对象。不满足条件时抛出 ValueError。"""
        interview = await self.get_interview(interview_id)
        if not interview:
            raise ValueError("INTERVIEW_NOT_FOUND")
        if interview.status != InterviewStatus.PENDING.value:
            raise ValueError("INTERVIEW_NOT_PENDING")
        return interview

    async def validate_for_answer(self, interview_id: uuid.UUID) -> InterviewModel:
        """校验面试可以提交回答，返回面试对象。不满足条件时抛出 ValueError。"""
        interview = await self.get_interview(interview_id)
        if not interview:
            raise ValueError("INTERVIEW_NOT_FOUND")
        if interview.status != InterviewStatus.IN_PROGRESS.value:
            raise ValueError("INTERVIEW_NOT_IN_PROGRESS")
        return interview

    async def is_report_generating(self, interview_id: uuid.UUID) -> bool:
        """检查面试报告是否正在生成中。"""
        interview = await self.get_interview(interview_id)
        if not interview:
            raise ValueError("INTERVIEW_NOT_FOUND")
        return interview.status == InterviewStatus.REPORT_GENERATING.value

    async def mark_failed(self, interview_id: uuid.UUID, error_msg: str) -> None:
        """标记面试为失败状态。"""
        from sqlalchemy import update

        await self._session.execute(
            update(InterviewModel).where(InterviewModel.id == interview_id).values(status=InterviewStatus.FAILED.value)
        )
        await self._session.commit()
        logger.error("Interview %s marked as failed: %s", interview_id, error_msg)

    async def get_interview_status(self, interview_id: uuid.UUID) -> dict:
        """获取面试状态概要。"""
        interview = await self.get_interview(interview_id)
        if not interview:
            raise ValueError("INTERVIEW_NOT_FOUND")

        q_result = await self._session.execute(
            select(InterviewQuestionModel)
            .where(InterviewQuestionModel.interview_id == interview_id)
            .order_by(InterviewQuestionModel.sequence_num)
        )
        questions = list(q_result.scalars().all())

        answered_count = 0
        current_question_num = None

        for q in questions:
            a_result = await self._session.execute(
                select(QuestionAnswerModel)
                .where(QuestionAnswerModel.question_id == q.id)
                .where(QuestionAnswerModel.is_followup == False)  # noqa: E712
            )
            if a_result.scalar_one_or_none():
                answered_count += 1
            elif current_question_num is None:
                current_question_num = q.sequence_num

        return {
            "interview_id": str(interview_id),
            "status": interview.status,
            "current_question_num": current_question_num,
            "total_questions": len(questions) if questions else interview.question_count,
            "answered_count": answered_count,
        }

    async def get_report(self, interview_id: uuid.UUID) -> InterviewReportModel | None:
        """获取面试报告。"""
        result = await self._session.execute(
            select(InterviewReportModel).where(InterviewReportModel.interview_id == interview_id)
        )
        return result.scalar_one_or_none()

    async def list_interviews(self, resume_id: uuid.UUID | None = None) -> list[dict]:
        """获取面试列表。"""
        query = select(InterviewModel).order_by(InterviewModel.created_at.desc())
        if resume_id:
            query = query.where(InterviewModel.resume_id == resume_id)

        result = await self._session.execute(query)
        interviews = list(result.scalars().all())

        items = []
        for iv in interviews:
            report_result = await self._session.execute(
                select(InterviewReportModel).where(InterviewReportModel.interview_id == iv.id)
            )
            report = report_result.scalar_one_or_none()

            items.append(
                {
                    "interview_id": str(iv.id),
                    "resume_id": str(iv.resume_id),
                    "status": iv.status,
                    "question_count": iv.question_count,
                    "overall_score": report.overall_score if report else None,
                    "recommendation": report.recommendation if report else None,
                    "created_at": iv.created_at,
                }
            )

        return items
