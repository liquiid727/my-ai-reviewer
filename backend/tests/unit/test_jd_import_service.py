"""JD import validation and storage compensation behavior."""

from __future__ import annotations

import uuid

import pytest

from backend.application.jd_import_service import JDImportError, JDImportResult, JDImportService
from backend.infrastructure.db.models import JobDescriptionModel


class FakeImportSession:
    def __init__(self, *, fail_second_flush: bool = False) -> None:
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0
        self.fail_second_flush = fail_second_flush

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        self.flushes += 1
        for value in self.added:
            if isinstance(value, JobDescriptionModel) and value.id is None:
                value.id = uuid.uuid4()
        if self.fail_second_flush and self.flushes == 2:
            raise RuntimeError("database write failed")

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


async def test_text_import_trims_and_enforces_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_dispatch(
        self: JDImportService,
        session: FakeImportSession,
        jd: JobDescriptionModel,
        **_: object,
    ) -> JDImportResult:
        return JDImportResult(jd=jd)

    monkeypatch.setattr(JDImportService, "_dispatch_or_mark_failed", no_dispatch)
    service = JDImportService()
    session = FakeImportSession()

    result = await service.import_text(session, raw_text="  Build resilient APIs  ")  # type: ignore[arg-type]
    assert result.jd.raw_text == "Build resilient APIs"
    assert session.commits == 1

    with pytest.raises(JDImportError, match="between 1"):
        await service.import_text(session, raw_text="   ")  # type: ignore[arg-type]
    with pytest.raises(JDImportError, match="between 1"):
        await service.import_text(session, raw_text="x" * 100_001)  # type: ignore[arg-type]


async def test_file_import_rolls_back_when_object_upload_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_upload(*_: object, **__: object) -> None:
        raise OSError("storage unavailable")

    monkeypatch.setattr("backend.application.jd_import_service.upload_file", fail_upload)
    session = FakeImportSession()

    with pytest.raises(JDImportError, match="Unable to store"):
        await JDImportService().import_file(
            session,  # type: ignore[arg-type]
            filename="role.txt",
            content_type="text/plain",
            data=b"Build services",
        )

    assert session.rollbacks == 1


async def test_file_import_compensates_object_when_database_write_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    removed: list[str] = []

    def upload(*_: object, **__: object) -> None:
        return None

    def remove(_bucket: str, object_name: str) -> None:
        removed.append(object_name)

    monkeypatch.setattr("backend.application.jd_import_service.upload_file", upload)
    monkeypatch.setattr("backend.application.jd_import_service.delete_file", remove)
    session = FakeImportSession(fail_second_flush=True)

    with pytest.raises(JDImportError, match="Unable to store"):
        await JDImportService().import_file(
            session,  # type: ignore[arg-type]
            filename="role.md",
            content_type="text/markdown",
            data=b"# Role",
        )

    assert session.rollbacks == 1
    assert len(removed) == 1
