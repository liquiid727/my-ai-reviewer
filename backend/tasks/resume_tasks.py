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
    async with async_session_factory() as session:
        resume = await step_fn(session, resume_id)
        return str(resume.status)


async def _mark_failed(resume_id: uuid.UUID, error: str) -> None:
    async with async_session_factory() as session:
        from backend.infrastructure.db.models import ResumeModel

        resume = await session.get(ResumeModel, resume_id)
        if resume:
            resume.status = "failed"
            resume.parse_error = error
            await session.commit()


@celery.task(bind=True, name="tasks.text_extract", time_limit=30, max_retries=0)
def text_extract_task(self, resume_id_str: str) -> str:
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
    pipeline = chain(
        text_extract_task.s(resume_id),
        llm_parse_task.s(resume_id),
        classify_task.s(resume_id),
        evaluate_task.s(resume_id),
    )
    pipeline.apply_async()
