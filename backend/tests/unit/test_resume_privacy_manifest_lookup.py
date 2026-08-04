"""Privacy manifests must be loaded by their unique resume_id, not their PK."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import Select

from backend.application.resume_service import pipeline as services


class _Session:
    def __init__(self, manifest: Any) -> None:
        self.manifest = manifest
        self.statement: Select[Any] | None = None

    async def get(self, _model: Any, _key: Any) -> None:
        raise AssertionError("manifest lookup must not use the manifest primary key")

    async def scalar(self, statement: Select[Any]) -> Any:
        self.statement = statement
        return self.manifest


@pytest.mark.asyncio
async def test_manifest_lookup_uses_unique_resume_id_column() -> None:
    resume_id = uuid.uuid4()
    manifest = object()
    session = _Session(manifest)

    result = await services.get_privacy_manifest(session, resume_id)  # type: ignore[arg-type]

    assert result is manifest
    assert session.statement is not None
    assert "resume_privacy_manifests.resume_id" in str(session.statement)
