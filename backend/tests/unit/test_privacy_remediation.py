from backend.domain.privacy.remediation import scrub_payload


def test_scrub_payload_masks_nested_legacy_resume_data() -> None:
    payload = {"raw_text": "张三\n电话: 13812345678", "facts": [{"email": "z@example.com"}]}

    masked, manifest = scrub_payload(payload)

    assert masked["raw_text"].startswith("[[PERSON_")
    assert "13812345678" not in str(masked)
    assert "z@example.com" not in str(masked)
    assert manifest["placeholders"]
