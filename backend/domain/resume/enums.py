"""简历领域枚举 —— 定义简历处理各阶段的状态和分类标签。"""

from enum import Enum


class ResumeStatus(str, Enum):
    """简历处理流水线的状态机。"""
    UPLOADED = "uploaded"             # 已上传，等待处理
    TEXT_PARSED = "text_parsed"       # 文本提取完成
    FACT_EXTRACTED = "fact_extracted"  # LLM 结构化提取完成
    CLASSIFIED = "classified"         # 规则分类完成
    EVALUATED = "evaluated"           # LLM 评估完成
    FAILED = "failed"                 # 处理失败


class ResumeSectionType(str, Enum):
    """简历中不同区块的类型。"""
    BASIC_INFO = "basic_info"                # 基本信息
    EDUCATION = "education"                  # 教育背景
    WORK_EXPERIENCE = "work_experience"      # 工作经历
    PROJECT_EXPERIENCE = "project_experience"  # 项目经历
    SKILLS = "skills"                        # 技能
    CERTIFICATES = "certificates"            # 证书
    OTHER = "other"                          # 其他


class FactType(str, Enum):
    """简历中可提取的事实类型。"""
    IDENTITY = "identity"              # 身份信息
    EDUCATION = "education"            # 教育经历
    WORK_EXPERIENCE = "work_experience"  # 工作经历
    PROJECT = "project"                # 项目经历
    SKILL = "skill"                    # 技能
    CERTIFICATE = "certificate"        # 证书
    INTERVIEW_CLUE = "interview_clue"  # 面试线索


class LLMProvider(str, Enum):
    """支持的 LLM 提供商。"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    CUSTOM = "custom"        # 自定义 OpenAI 兼容接口
