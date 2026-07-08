from enum import Enum

# 定义建立状态
class ResumeStatus(str, Enum):
    UPLOADED = "uploaded"
    TEXT_PARSED = "text_parsed"
    FACT_EXTRACTED = "fact_extracted"
    CLASSIFIED = "classified"
    EVALUATED = "evaluated"
    FAILED = "failed"

# 定义简历分区
class ResumeSectionType(str, Enum):
    BASIC_INFO = "basic_info"
    EDUCATION = "education"
    WORK_EXPERIENCE = "work_experience"
    PROJECT_EXPERIENCE = "project_experience"
    SKILLS = "skills"
    CERTIFICATES = "certificates"
    OTHER = "other"

# 定义简历fact类型
class FactType(str, Enum):
    IDENTITY = "identity"
    EDUCATION = "education"
    WORK_EXPERIENCE = "work_experience"
    PROJECT = "project"
    SKILL = "skill"
    CERTIFICATE = "certificate"
    INTERVIEW_CLUE = "interview_clue"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    CUSTOM = "custom"
