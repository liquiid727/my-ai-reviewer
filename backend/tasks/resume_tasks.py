"""Celery 异步任务 —— 简历处理流水线的四个步骤以 Celery chain 形式串联执行。

流水线顺序：文本提取 → LLM 解析 → 规则分类 → LLM 评估
每个步骤接收上一步的状态，如果上一步失败则直接跳过。
"""

import asyncio
import logging
import uuid

from celery import chain

from backend.celery_app import celery
from backend.infrastructure.db.database import async_session_factory
from backend.domain.resume import services

logger = logging.getLogger(__name__)


async def _run_step(
    step_fn,  # type: ignore[type-arg]
    resume_id: uuid.UUID,
) -> str:
    """通用步骤执行器：在异步会话中运行指定的服务函数。"""
    async with async_session_factory() as session:
        resume = await step_fn(session, resume_id)
        return str(resume.status)


async def _mark_failed(resume_id: uuid.UUID, error: str) -> None:
    """将简历标记为失败状态并记录错误信息。"""
    async with async_session_factory() as session:
        from backend.infrastructure.db.models import ResumeModel

        resume = await session.get(ResumeModel, resume_id)
        if resume:
            resume.status = "failed"
            resume.parse_error = error
            await session.commit()


@celery.task(bind=True, name="tasks.text_extract", time_limit=30, max_retries=0)
def text_extract_task(self, resume_id_str: str) -> str:
    """步骤一：从文件中提取原始文本（限时 30 秒，不重试）。"""
    resume_id = uuid.UUID(resume_id_str)
    try:
        return asyncio.run(_run_step(services.extract_text, resume_id))
    except Exception as exc:
        asyncio.run(_mark_failed(resume_id, str(exc)))
        return "failed"


@celery.task(
    bind=True,
    name="tasks.llm_parse",
    time_limit=120,
    max_retries=2,
    default_retry_delay=30,
)
def llm_parse_task(self, prev_status: str, resume_id_str: str) -> str:
    """步骤二：调用 LLM 进行结构化提取（限时 120 秒，最多重试 2 次）。"""
    if prev_status == "failed":
        return "failed"
    resume_id = uuid.UUID(resume_id_str)
    try:
        return asyncio.run(_run_step(services.extract_facts, resume_id))
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            asyncio.run(_mark_failed(resume_id, str(exc)))
            return "failed"


@celery.task(bind=True, name="tasks.classify", time_limit=30, max_retries=0)
def classify_task(self, prev_status: str, resume_id_str: str) -> str:
    """步骤三：基于规则进行简历分类（限时 30 秒，不重试）。"""
    if prev_status == "failed":
        return "failed"
    resume_id = uuid.UUID(resume_id_str)
    try:
        return asyncio.run(_run_step(services.classify_resume, resume_id))
    except Exception as exc:
        asyncio.run(_mark_failed(resume_id, str(exc)))
        return "failed"


@celery.task(
    bind=True,
    name="tasks.evaluate",
    time_limit=120,
    max_retries=2,
    default_retry_delay=30,
)
def evaluate_task(self, prev_status: str, resume_id_str: str) -> str:
    """步骤四：调用 LLM 进行多维度评估（限时 120 秒，最多重试 2 次）。"""
    if prev_status == "failed":
        return "failed"
    resume_id = uuid.UUID(resume_id_str)
    try:
        return asyncio.run(_run_step(services.evaluate_resume, resume_id))
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            asyncio.run(_mark_failed(resume_id, str(exc)))
            return "failed"


def process_resume_pipeline(resume_id: str) -> None:
    """构建并派发完整的简历处理流水线（四步 chain）。"""
    pipeline = chain(
        text_extract_task.s(resume_id),
        llm_parse_task.s(resume_id),
        classify_task.s(resume_id),
        evaluate_task.s(resume_id),
    )
    pipeline.apply_async()
