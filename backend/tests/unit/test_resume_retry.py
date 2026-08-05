"""Resume retry routing for approved masked data and stale workers."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.resume_service import privacy
from backend.domain.resume.enums import ResumeStatus
from backend.infrastructure.db.models import ResumeModel


class _Session:
    def __init__(self, resume: Any, manifest: Any) -> None:
        self.resume = resume
        self.manifest = manifest
        self.commits = 0

    async def get(self, model: Any, _resume_id: Any) -> Any:
        if model is ResumeModel:
            return self.resume
        return None

    async def scalar(self, _statement: Any) -> Any:
        return self.manifest

    async def commit(self) -> None:
        self.commits += 1


def _approved_resume(status: str, *, stale: bool = True) -> tuple[Any, Any, uuid.UUID]:
    resume_id = uuid.uuid4()
    resume = SimpleNamespace(
        id=resume_id,
        status=status,
        masked_text="Candidate [[PERSON_01]]",
        file_id=None,
        parse_error="old failure" if status == ResumeStatus.FAILED.value else None,
        updated_at=(
            datetime.now(timezone.utc) - timedelta(seconds=601)
            if stale
            else datetime.now(timezone.utc)
        ),
    )
    manifest = SimpleNamespace(status="approved")
    return resume, manifest, resume_id


@pytest.mark.asyncio
async def test_failed_approved_resume_retries_from_masked_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume, manifest, resume_id = _approved_resume(ResumeStatus.FAILED.value)
    dispatched: list[str] = []
    monkeypatch.setattr(
        privacy,
        "process_masked_resume_pipeline",
        lambda value: dispatched.append(value),
    )

    result = await privacy.retry_failed_resume(
        cast(AsyncSession, _Session(resume, manifest)),
        resume,
    )

    assert result == ResumeStatus.TEXT_MASKED.value
    assert resume.status == ResumeStatus.TEXT_MASKED.value
    assert resume.parse_error is None
    assert dispatched == [str(resume_id)]


@pytest.mark.asyncio
async def test_stale_masked_status_can_requeue_existing_stuck_resume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume, manifest, resume_id = _approved_resume(ResumeStatus.TEXT_MASKED.value)
    dispatched: list[str] = []
    monkeypatch.setattr(
        privacy,
        "process_masked_resume_pipeline",
        lambda value: dispatched.append(value),
    )

    result = await privacy.retry_failed_resume(
        cast(AsyncSession, _Session(resume, manifest)),
        resume,
    )

    assert result == ResumeStatus.TEXT_MASKED.value
    assert dispatched == [str(resume_id)]


@pytest.mark.asyncio
async def test_fresh_masked_status_is_not_requeued(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume, manifest, _resume_id = _approved_resume(ResumeStatus.LLM_PARSING.value, stale=False)
    monkeypatch.setattr(
        privacy,
        "process_masked_resume_pipeline",
        lambda _value: pytest.fail("fresh task must not be duplicated"),
    )

    with pytest.raises(ValueError, match="still active"):
        await privacy.retry_failed_resume(
            cast(AsyncSession, _Session(resume, manifest)),
            resume,
        )
