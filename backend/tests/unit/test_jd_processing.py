"""JD worker pure-rule coverage: normalization, hashing, and manual provenance."""

import uuid

import pytest

from backend.application.jd_import_service import MAX_JD_FILE_SIZE, JDImportError, _validate_file
from backend.application.jd_service.processing import JDProcessingService
from backend.domain.jd.policies import content_hash, normalize_jd_text
from backend.domain.jd.schemas import ExtractedSkill, JDExtraction
from backend.infrastructure.db.models import FileModel, JobDescriptionModel


def test_normalization_is_stable_for_equivalent_whitespace_and_unicode() -> None:
    normalized = normalize_jd_text("  Python\r\n\r\nＦａｓｔＡＰＩ  ")

    assert normalized == "Python FastAPI"
    assert content_hash(normalized) == content_hash("Python FastAPI")


def test_llm_merge_preserves_manual_fields_unless_explicitly_overwritten() -> None:
    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        raw_text="A long enough job description",
        title="Manual title",
        field_sources={"title": "manual"},
    )
    extraction = JDExtraction(
        title="LLM title",
        company="Example",
        location="Shanghai",
        required_skills=[ExtractedSkill(name="Python", evidence="Python")],
        preferred_skills=[],
        responsibilities=["Build APIs"],
        seniority="senior",
    )

    JDProcessingService._merge_extraction(jd, extraction, overwrite_manual=False)

    assert jd.title == "Manual title"
    assert jd.company == "Example"
    assert jd.field_sources["title"] == "manual"
    assert jd.field_sources["company"] == "llm"

    JDProcessingService._merge_extraction(jd, extraction, overwrite_manual=True)

    assert jd.title == "LLM title"
    assert jd.field_sources["title"] == "llm"


def test_jd_file_validation_accepts_allowed_types_and_rejects_mismatches() -> None:
    assert _validate_file("role.md", "text/markdown", b"# Role") == ".md"

    with pytest.raises(JDImportError, match="MIME"):
        _validate_file("role.pdf", "text/plain", b"not really a PDF")
    with pytest.raises(JDImportError, match="Only PDF"):
        _validate_file("role.exe", "application/octet-stream", b"bad")
    with pytest.raises(JDImportError, match="10MB"):
        _validate_file("role.txt", "text/plain", b"x" * (MAX_JD_FILE_SIZE + 1))


async def test_file_parser_failure_is_exposed_to_the_worker_as_a_source_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingParser:
        version = "test-parser"

        def parse(self, _: str) -> object:
            raise ValueError("broken document")

    class FakeSession:
        async def get(self, model: object, identifier: uuid.UUID) -> object:
            assert model is FileModel
            assert identifier == source_file_id
            return FileModel(
                id=source_file_id,
                original_name="role.txt",
                storage_path="jd/test/role.txt",
                content_type="text/plain",
                size_bytes=4,
                sha256_hash="0" * 64,
                owner_type="job_description",
                owner_id=uuid.uuid4(),
            )

        async def rollback(self) -> None:
            return None

    source_file_id = uuid.uuid4()
    jd = JobDescriptionModel(
        id=uuid.uuid4(),
        source_type="file",
        source_file_id=source_file_id,
        raw_text="",
    )
    monkeypatch.setattr("backend.application.jd_service.processing.download_file", lambda *_: b"text")
    monkeypatch.setattr("backend.application.jd_service.processing.get_parser", lambda _: FailingParser())

    with pytest.raises(ValueError, match="broken document"):
        await JDProcessingService()._read_source(FakeSession(), jd)  # type: ignore[arg-type]
