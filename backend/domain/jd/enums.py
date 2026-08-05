"""JD library lifecycle values shared by API, services, and persistence."""

from enum import StrEnum


class JDSourceType(StrEnum):
    TEXT = "text"
    FILE = "file"
    URL = "url"
    IMAGE = "image"
    MANUAL = "manual"


class JDStatus(StrEnum):
    PROCESSING = "processing"
    DUPLICATE_PENDING = "duplicate_pending"
    NEEDS_REVIEW = "needs_review"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


class JDProcessingStep(StrEnum):
    QUEUED = "queued"
    SOURCE_EXTRACT = "source_extract"
    DUPLICATE_CHECK = "duplicate_check"
    STRUCTURE_PARSE = "structure_parse"
    LLM_EXTRACT = "llm_extract"
    REVIEW = "review"
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
