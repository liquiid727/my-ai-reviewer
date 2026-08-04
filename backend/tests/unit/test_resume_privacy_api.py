"""Privacy review endpoint orchestration."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1 import resume as api
from backend.infrastructure.db.models import ResumeModel


class _Session:
    def __init__(self, resume: Any, manifest: Any) -> None:
        self.resume = resume
        self.manifest = manifest
        self.commits = 0

    async def get(self, model: Any, key: Any) -> Any:
        if model is ResumeModel:
            return self.resume
        return None

    async def scalar(self, _statement: Any) -> Any:
        return self.manifest

    async def commit(self) -> None:
        self.commits += 1

    async def delete(self, value: Any) -> None:
        return None


def _state() -> tuple[uuid.UUID, Any, Any]:
    resume_id = uuid.uuid4()
    resume = SimpleNamespace(
        id=resume_id,
        status="privacy_review_required",
        masked_text="姓名：[[PERSON_01]]\n客户：秘密平台",
        file_id=None,
        parse_error=None,
    )
    manifest = SimpleNamespace(
        resume_id=resume_id,
        status="review_required",
        revision=2,
        policy_version="resume-privacy-v1",
        engine_version="local-redactor-v1",
        placeholders=[
            {
                "token": "[[PERSON_01]]",
                "entity_type": "person",
                "occurrence_count": 1,
                "context": "姓名：[[PERSON_01]]",
                "detector": "layout.person",
            }
        ],
        risk_flags=["manual_review"],
        quarantine_path=f"{resume_id}/source.enc",
        quarantine_expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        reviewed_at=None,
    )
    return resume_id, resume, manifest


@pytest.mark.asyncio
async def test_privacy_review_response_is_masked_and_no_store() -> None:
    resume_id, resume, manifest = _state()
    response = Response()

    result = await api.get_privacy_review(resume_id, response, cast(AsyncSession, _Session(resume, manifest)))

    assert result.data["masked_text"] == resume.masked_text
    assert result.data["revision"] == 2
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.asyncio
async def test_approve_privacy_deletes_quarantine_and_dispatches_masked_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume_id, resume, manifest = _state()
    deleted: list[tuple[str, str]] = []
    dispatched: list[str] = []
    monkeypatch.setattr(
        "backend.application.resume_service.privacy.delete_file",
        lambda bucket, path: deleted.append((bucket, path)),
    )
    monkeypatch.setattr(
        "backend.application.resume_service.privacy.process_masked_resume_pipeline",
        lambda value: dispatched.append(value),
    )
    monkeypatch.setattr(
        "backend.application.resume_service.privacy.get_settings",
        lambda: SimpleNamespace(MINIO_BUCKET_QUARANTINE="quarantine"),
    )

    result = await api.approve_privacy(
        resume_id,
        api.PrivacyApproveRequest(base_revision=2),
        cast(AsyncSession, _Session(resume, manifest)),
    )

    assert result.data["status"] == "text_masked"
    assert manifest.status == "approved"
    assert manifest.quarantine_path is None
    assert deleted == [("quarantine", f"{resume_id}/source.enc")]
    assert dispatched == [str(resume_id)]
