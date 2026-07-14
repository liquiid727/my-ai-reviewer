"""analyze_resume 节点 —— 从数据库加载简历解析结果到 LangGraph 状态。"""

import logging
import uuid

from sqlalchemy import select

from backend.infrastructure.db.database import async_session_factory
from backend.infrastructure.db.models import ResumeModel
from backend.workflow.state import InterviewState

logger = logging.getLogger(__name__)


async def analyze_resume(state: InterviewState) -> dict:
    """加载简历 parsed_result 到 state。"""
    resume_id = uuid.UUID(state["resume_id"])

    async with async_session_factory() as session:
        result = await session.execute(select(ResumeModel).where(ResumeModel.id == resume_id))
        resume = result.scalar_one_or_none()

    if not resume or not resume.parsed_result:
        raise ValueError(f"Resume {resume_id} not found or not parsed")

    logger.info("Loaded resume data for %s", resume_id)
    return {"resume_data": resume.parsed_result}
