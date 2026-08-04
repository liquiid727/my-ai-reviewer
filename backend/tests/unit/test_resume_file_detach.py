"""Resume source files must be detached before their rows are deleted."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.resume_service.pipeline import detach_resume_file


class _Session:
    def __init__(self) -> None:
        self.events: list[str] = []

    async def flush(self) -> None:
        self.events.append("flush")

    async def delete(self, _value: Any) -> None:
        self.events.append("delete")


@pytest.mark.asyncio
async def test_detach_resume_file_flushes_foreign_key_update_before_delete() -> None:
    session = _Session()
    resume = SimpleNamespace(file_id=uuid.uuid4())
    file_record = object()

    await detach_resume_file(cast(AsyncSession, session), resume, file_record)  # type: ignore[arg-type]

    assert resume.file_id is None
    assert session.events == ["flush", "delete"]
