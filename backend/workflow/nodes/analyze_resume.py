"""analyze_resume 节点 —— 加载出题用简历数据到 LangGraph 状态。

优先使用面试自带的 resume_snapshot（草稿面试的脱敏内容快照），
否则按 resume_id 从数据库加载简历解析结果。
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select

from backend.infrastructure.db.database import async_session_factory
from backend.infrastructure.db.models import InterviewModel, ResumeModel
from backend.workflow.state import InterviewState

logger = logging.getLogger(__name__)


async def analyze_resume(state: InterviewState) -> dict[str, Any]:
    """加载简历快照或 parsed_result 到 state。"""
    interview_id = uuid.UUID(state["interview_id"])

    async with async_session_factory() as session:
        result = await session.execute(select(InterviewModel).where(InterviewModel.id == interview_id))
        interview = result.scalar_one_or_none()

        # 草稿面试：出题数据来自创建时的脱敏快照，不依赖已解析简历
        if interview is not None and interview.resume_snapshot:
            logger.info("Loaded draft snapshot for interview %s", interview_id)
            return {"resume_data": interview.resume_snapshot}

        resume_id = uuid.UUID(state["resume_id"])
        resume_result = await session.execute(select(ResumeModel).where(ResumeModel.id == resume_id))
        resume = resume_result.scalar_one_or_none()

    if not resume or not resume.parsed_result:
        raise ValueError(f"Resume {resume_id} not found or not parsed")

    logger.info("Loaded resume data for %s", resume_id)
    return {"resume_data": resume.parsed_result}
