"""Upload quarantine and privacy pipeline contracts."""

from __future__ import annotations

import uuid

from cryptography.fernet import Fernet

from backend.application.resume_service import prepare_quarantined_upload
from backend.tasks.resume_tasks import privacy_allows_llm


def test_prepare_upload_encrypts_source_and_discards_original_filename() -> None:
    source = b"Zhang San zhangsan@example.com"
    resume_id = uuid.uuid4()

    prepared = prepare_quarantined_upload(
        resume_id=resume_id,
        filename="Zhang San confidential resume.pdf",
        file_data=source,
        encryption_key=Fernet.generate_key().decode("ascii"),
    )

    assert prepared.safe_name == "resume.pdf"
    assert prepared.object_name.startswith(f"{resume_id}/")
    assert prepared.object_name.endswith(".enc")
    assert source not in prepared.encrypted_data
    assert prepared.content_hash != ""


def test_only_approved_masked_status_can_enter_llm_pipeline() -> None:
    assert privacy_allows_llm("text_masked") is True
    assert privacy_allows_llm("privacy_review_required") is False
    assert privacy_allows_llm("privacy_scanning") is False
    assert privacy_allows_llm("failed") is False
