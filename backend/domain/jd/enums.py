"""JD library lifecycle values shared by API, services, and persistence."""

from enum import StrEnum


class JDSourceType(StrEnum):
    TEXT = "text"
    FILE = "file"
    URL = "url"


class JDStatus(StrEnum):
    PROCESSING = "processing"
    DUPLICATE_PENDING = "duplicate_pending"
    READY = "ready"
    FAILED = "failed"


class JDProcessingStep(StrEnum):
    QUEUED = "queued"
    SOURCE_EXTRACT = "source_extract"
    DUPLICATE_CHECK = "duplicate_check"
    LLM_EXTRACT = "llm_extract"
    DONE = "done"


STRUCTURED_FIELD_NAMES = (
    "title",
    "company",
    "location",
    "seniority",
    "responsibilities",
    "required_skills",
    "preferred_skills",
)
