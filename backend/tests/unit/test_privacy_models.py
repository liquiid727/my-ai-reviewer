"""RIP-009 persistence and API schema contracts."""

from backend.api.v1.schemas import ResumeDetailData, ResumeUploadData
from backend.infrastructure.db.models import (
    ResumeDraftModel,
    ResumeModel,
    ResumePrivacyManifestModel,
    ResumeSectionModel,
)


def test_resume_orm_uses_masked_text_and_has_one_privacy_manifest() -> None:
    assert "masked_text" in ResumeModel.__table__.columns
    assert "raw_text" not in ResumeModel.__table__.columns
    assert ResumePrivacyManifestModel.__tablename__ == "resume_privacy_manifests"
    assert ResumePrivacyManifestModel.resume_id.property.columns[0].unique is True


def test_draft_has_safe_privacy_manifest_column() -> None:
    assert "privacy_manifest" in ResumeDraftModel.__table__.columns


def test_privacy_manifest_does_not_absorb_resume_section_columns() -> None:
    assert "section_index" in ResumeSectionModel.__table__.columns
    assert "raw_text" in ResumeSectionModel.__table__.columns
    assert "section_index" not in ResumePrivacyManifestModel.__table__.columns


def test_resume_api_contract_does_not_expose_file_id_or_raw_text() -> None:
    assert "file_id" not in ResumeUploadData.model_fields
    assert "raw_text" not in ResumeDetailData.model_fields
    assert "masked_text" in ResumeDetailData.model_fields
