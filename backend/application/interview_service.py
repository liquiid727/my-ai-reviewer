"""面试业务编排服务 —— 协调 LangGraph 图和数据库操作。"""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.jd_matching.freshness import current_match_fingerprint, stale_reasons
from backend.domain.interview.enums import InterviewStatus
from backend.domain.jd.matching_v2 import MatchStatus, stable_json
from backend.domain.privacy import PrivacyGuard, PrivacyViolationError
from backend.infrastructure.db.models import (
    CandidateProfileModel,
    InterviewModel,
    InterviewQuestionModel,
    InterviewReportModel,
    JDMatchResultModel,
    JobDescriptionModel,
    QuestionAnswerModel,
    ResumeDraftModel,
    ResumeModel,
)
from backend.infrastructure.llm.gateway import LLMGateway

logger = logging.getLogger(__name__)


async def get_interview_llm_gateway(session: AsyncSession) -> LLMGateway:
    """Build the interview LLM gateway from the active verified database config."""
    from backend.application.llm_config_service import get_active_verified_config

    config = await get_active_verified_config(session)
    if config is None:
        await session.rollback()
        raise ValueError("LLM_NOT_READY")

    gateway = LLMGateway.from_config(config)
    # The gateway has copied the provider credentials; do not hold a DB
    # transaction while waiting for an external model response.
    await session.rollback()
    return gateway


class InterviewService:
    """面试服务：创建面试、启动面试流程、提交回答、查询状态/报告。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_interview(
        self,
        resume_id: uuid.UUID | None = None,
        jd_text: str | None = None,
        question_count: int = 5,
        draft_id: uuid.UUID | None = None,
        jd_id: uuid.UUID | None = None,
        match_result_id: uuid.UUID | None = None,
    ) -> InterviewModel:
        """创建面试会话：基于已评估简历，或基于简历草稿内容快照。"""
        if draft_id is not None:
            if resume_id is not None:
                raise ValueError("INVALID_REQUEST")
            return await self._create_interview_from_draft(
                draft_id,
                jd_text,
                question_count,
                jd_id=jd_id,
                match_result_id=match_result_id,
            )
        if resume_id is None:
            raise ValueError("INVALID_REQUEST")
        if match_result_id is not None and jd_id is None:
            raise ValueError("MATCH_REQUIRES_JD")
        if jd_id is None and not (jd_text or "").strip():
            raise ValueError("JD_REQUIRED")

        result = await self._session.execute(select(ResumeModel).where(ResumeModel.id == resume_id))
        resume = result.scalar_one_or_none()
        if not resume:
            raise ValueError("RESUME_NOT_FOUND")

        valid_statuses = {"evaluated", "classified"}
        if resume.status not in valid_statuses:
            raise ValueError("RESUME_NOT_READY")

        jd_snapshot, match_snapshot, context_fingerprint = await self._build_jd_match_context(
            resume_id=resume_id,
            jd_id=jd_id,
            match_result_id=match_result_id,
            jd_text=jd_text,
        )

        interview = InterviewModel(
            resume_id=resume_id,
            jd_text=jd_text or (jd_snapshot or {}).get("raw_text"),
            jd_id=jd_id,
            match_result_id=match_result_id,
            jd_context_snapshot=jd_snapshot,
            match_context_snapshot=match_snapshot,
            context_fingerprint=context_fingerprint,
            question_count=question_count,
            status=InterviewStatus.PENDING.value,
            graph_thread_id=str(uuid.uuid4()),
        )
        self._session.add(interview)
        await self._session.commit()
        await self._session.refresh(interview)

        logger.info("Created interview %s for resume %s", interview.id, resume_id)
        return interview

    async def _create_interview_from_draft(
        self,
        draft_id: uuid.UUID,
        jd_text: str | None,
        question_count: int,
        *,
        jd_id: uuid.UUID | None = None,
        match_result_id: uuid.UUID | None = None,
    ) -> InterviewModel:
        """从简历草稿创建面试：以草稿当前内容（已脱敏）作为出题快照。

        草稿在保存时已经过本地脱敏；此处再用 PrivacyGuard 做 fail-closed
        拦截，任何直接标识符泄露风险都会阻止创建而不是降级发送原文。
        """
        result = await self._session.execute(select(ResumeDraftModel).where(ResumeDraftModel.id == draft_id))
        draft = result.scalar_one_or_none()
        if not draft:
            raise ValueError("DRAFT_NOT_FOUND")

        content = draft.content or {}
        snapshot: dict[str, Any] = {
            "source": "builder_draft",
            "draft_title": draft.title,
            "identity": content.get("identity", {}),
            "summary": content.get("summary", ""),
            "sections": content.get("sections", []),
        }
        try:
            PrivacyGuard().assert_masked(snapshot)
        except PrivacyViolationError:
            raise ValueError("DRAFT_NOT_MASKED") from None

        if match_result_id is not None and jd_id is None:
            raise ValueError("MATCH_REQUIRES_JD")
        if jd_id is None and not (jd_text or "").strip():
            raise ValueError("JD_REQUIRED")
        jd_snapshot, match_snapshot, context_fingerprint = await self._build_jd_match_context(
            resume_id=draft.resume_id,
            jd_id=jd_id,
            match_result_id=match_result_id,
            jd_text=jd_text,
        )

        interview = InterviewModel(
            resume_id=draft.resume_id,
            resume_snapshot=snapshot,
            jd_text=jd_text or (jd_snapshot or {}).get("raw_text"),
            jd_id=jd_id,
            match_result_id=match_result_id,
            jd_context_snapshot=jd_snapshot,
            match_context_snapshot=match_snapshot,
            context_fingerprint=context_fingerprint,
            question_count=question_count,
            status=InterviewStatus.PENDING.value,
            graph_thread_id=str(uuid.uuid4()),
        )
        self._session.add(interview)
        await self._session.commit()
        await self._session.refresh(interview)

        logger.info("Created interview %s from draft %s", interview.id, draft_id)
        return interview

    async def _build_jd_match_context(
        self,
        *,
        resume_id: uuid.UUID | None,
        jd_id: uuid.UUID | None,
        match_result_id: uuid.UUID | None,
        jd_text: str | None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
        jd_snapshot: dict[str, Any] | None = None
        match_snapshot: dict[str, Any] | None = None
        if jd_id is not None:
            jd = await self._session.get(JobDescriptionModel, jd_id)
            if jd is None:
                raise ValueError("JD_NOT_FOUND")
            if jd.status != "ready":
                raise ValueError("JD_NOT_READY")
            jd_snapshot = {
                "id": str(jd.id),
                "title": jd.title,
                "company": jd.company,
                "location": jd.location,
                "seniority": jd.seniority,
                "required_skills": jd.required_skills,
                "responsibilities": jd.responsibilities,
                "raw_text": jd.raw_text[:10_000],
                "structured_revision": getattr(jd, "structured_revision", 1),
            }
        elif jd_text:
            jd_snapshot = {"source": "inline_text", "raw_text": jd_text[:10_000]}
        if match_result_id is not None:
            if resume_id is None:
                raise ValueError("INVALID_REQUEST")
            match = await self._session.get(JDMatchResultModel, match_result_id)
            if match is None:
                raise ValueError("MATCH_NOT_FOUND")
            if match.jd_id != jd_id or match.resume_id != resume_id:
                raise ValueError("MATCH_RESOURCE_MISMATCH")
            if match.status != MatchStatus.READY.value:
                raise ValueError("MATCH_NOT_READY")
            profile = (
                await self._session.execute(
                    select(CandidateProfileModel).where(CandidateProfileModel.resume_id == resume_id)
                )
            ).scalar_one_or_none()
            jd = await self._session.get(JobDescriptionModel, jd_id) if jd_id is not None else None
            if jd is None or profile is None:
                raise ValueError("MATCH_RESOURCE_MISMATCH")
            expected = current_match_fingerprint(
                jd=jd, profile=profile, provider=match.provider, model_name=match.model_name
            )
            reasons = stale_reasons(
                match, expected_fingerprint=expected, provider=match.provider, model_name=match.model_name
            )
            if reasons:
                raise ValueError("MATCH_STALE")
            match_snapshot = {
                "id": str(match.id),
                "mode": match.mode,
                "input_fingerprint": match.input_fingerprint,
                "match_score": match.match_score,
                "recommendation": match.recommendation,
                "hard_filters": match.hard_filters,
                "dimension_scores": (match.dimension_scores or [])[:7],
                "gap": (match.gap or [])[:10],
                "evidence": (match.evidence or [])[:20],
                "matcher_version": match.matcher_version,
                "prompt_version": match.prompt_version,
                "schema_version": match.schema_version,
                "provider": match.provider,
                "model": match.model_name,
            }
        payload = {"jd": jd_snapshot, "match": match_snapshot}
        return jd_snapshot, match_snapshot, stable_json(payload) if jd_snapshot or match_snapshot else None

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

    async def get_interview_status(self, interview_id: uuid.UUID) -> dict[str, Any]:
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

    async def list_interviews(self, resume_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
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
                    "resume_id": str(iv.resume_id) if iv.resume_id else None,
                    "is_draft_interview": iv.resume_snapshot is not None,
                    "status": iv.status,
                    "question_count": iv.question_count,
                    "overall_score": report.overall_score if report else None,
                    "recommendation": report.recommendation if report else None,
                    "created_at": iv.created_at,
                }
            )

        return items
