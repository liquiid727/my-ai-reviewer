"""Celery 异步任务 —— 简历处理流水线的四个步骤以 Celery chain 形式串联执行。

流水线顺序：文本提取 → LLM 解析 → 规则分类 → LLM 评估
每个步骤接收上一步的状态，如果上一步失败则直接跳过。
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, TypeVar

from celery import chain
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.resume_service import pipeline as resume_pipeline
from backend.celery_app import celery
from backend.infrastructure.db.database import async_session_factory
from backend.infrastructure.db.models import ResumeModel

logger = logging.getLogger(__name__)

_T = TypeVar("_T")
_loop_local = threading.local()


def _run_async(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run an async coroutine on a per-thread event loop reused across tasks.

    Celery prefork/thread workers must not call ``asyncio.run`` per step: that
    closes the loop and breaks asyncpg / SQLAlchemy async engines bound to it.
    """
    loop = getattr(_loop_local, "loop", None)
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _loop_local.loop = loop
    return loop.run_until_complete(coro)


def privacy_allows_llm(status: str) -> bool:
    return status == "text_masked"


async def _run_step(
    step_fn: Callable[[AsyncSession, uuid.UUID], Awaitable[ResumeModel]],
    resume_id: uuid.UUID,
) -> str:
    """通用步骤执行器：在异步会话中运行指定的服务函数。"""
    async with async_session_factory() as session:
        resume = await step_fn(session, resume_id)
        return str(resume.status)


async def _mark_failed(resume_id: uuid.UUID, error: str) -> None:
    """将简历标记为失败状态并记录错误信息。"""
    async with async_session_factory() as session:
        resume = await session.get(ResumeModel, resume_id)
        if resume:
            resume.status = "failed"
            resume.parse_error = error
            await session.commit()


@celery.task(bind=True, name="tasks.text_extract", time_limit=30, max_retries=0)  # type: ignore[untyped-decorator]
def text_extract_task(self: Any, resume_id_str: str) -> str:
    """步骤一：从文件中提取原始文本（限时 30 秒，不重试）。"""
    resume_id = uuid.UUID(resume_id_str)
    try:
        return _run_async(_run_step(resume_pipeline.extract_text, resume_id))
    except Exception as exc:
        _run_async(_mark_failed(resume_id, str(exc)))
        return "failed"


@celery.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="tasks.llm_parse",
    time_limit=120,
    max_retries=2,
    default_retry_delay=30,
)
def llm_parse_task(self: Any, prev_status: str, resume_id_str: str) -> str:
    """步骤二：调用 LLM 进行结构化提取（限时 120 秒，最多重试 2 次）。"""
    if not privacy_allows_llm(prev_status):
        return prev_status
    resume_id = uuid.UUID(resume_id_str)
    try:
        return _run_async(_run_step(resume_pipeline.extract_facts, resume_id))
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _run_async(_mark_failed(resume_id, str(exc)))
            return "failed"


@celery.task(bind=True, name="tasks.classify", time_limit=30, max_retries=0)  # type: ignore[untyped-decorator]
def classify_task(self: Any, prev_status: str, resume_id_str: str) -> str:
    """步骤三：基于规则进行简历分类（限时 30 秒，不重试）。"""
    if prev_status != "fact_extracted":
        return prev_status
    resume_id = uuid.UUID(resume_id_str)
    try:
        return _run_async(_run_step(resume_pipeline.classify_resume, resume_id))
    except Exception as exc:
        _run_async(_mark_failed(resume_id, str(exc)))
        return "failed"


@celery.task(  # type: ignore[untyped-decorator]
    bind=True,
    name="tasks.evaluate",
    time_limit=120,
    max_retries=2,
    default_retry_delay=30,
)
def evaluate_task(self: Any, prev_status: str, resume_id_str: str) -> str:
    """步骤四：调用 LLM 进行多维度评估（限时 120 秒，最多重试 2 次）。"""
    if prev_status != "classified":
        return prev_status
    resume_id = uuid.UUID(resume_id_str)
    try:
        return _run_async(_run_step(resume_pipeline.evaluate_resume, resume_id))
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _run_async(_mark_failed(resume_id, str(exc)))
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


def process_masked_resume_pipeline(resume_id: str) -> None:
    """Resume an approved review at the first LLM step."""
    pipeline = chain(
        llm_parse_task.s("text_masked", resume_id),
        classify_task.s(resume_id),
        evaluate_task.s(resume_id),
    )
    pipeline.apply_async()
