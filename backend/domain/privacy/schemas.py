"""Privacy value objects. Manifests intentionally never retain source values."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PrivacyPlaceholder(BaseModel):
    token: str
    entity_type: str
    occurrence_count: int = Field(ge=1)
    context: str = ""
    detector: str


class PrivacyManifest(BaseModel):
    policy_version: str = "resume-privacy-v1"
    engine_version: str = "local-redactor-v1"
    placeholders: list[PrivacyPlaceholder] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class RedactionResult(BaseModel):
    masked_text: str
    manifest: PrivacyManifest
