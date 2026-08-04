"""简历领域枚举 —— 定义简历处理各阶段的状态和分类标签。"""

from enum import Enum


class ResumeStatus(str, Enum):
    """简历处理流水线的状态机。"""
    UPLOADED = "uploaded"             # 已上传，等待处理
    PRIVACY_SCANNING = "privacy_scanning"
    PRIVACY_REVIEW_REQUIRED = "privacy_review_required"
    TEXT_MASKED = "text_masked"
    TEXT_PARSED = "text_masked"       # Backward-compatible symbolic alias
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
    AWARDS = "awards"                        # 奖项荣誉
    SELF_EVALUATION = "self_evaluation"      # 自我评价
    OTHER = "other"                          # 其他


class SkillCategory(str, Enum):
    """技能分类（PRD §5 要求的 10 类固定分类 + other 兜底）。"""
    PROGRAMMING_LANGUAGE = "programming_language"  # 编程语言
    FRAMEWORK = "framework"                        # 框架
    DATABASE = "database"                          # 数据库
    CACHE = "cache"                                # 缓存
    MQ = "mq"                                      # 消息队列
    CLOUD_NATIVE = "cloud_native"                  # 云原生
    AI = "ai"                                      # AI / 机器学习
    DEVOPS = "devops"                              # DevOps
    TESTING = "testing"                            # 测试
    ARCHITECTURE = "architecture"                  # 架构
    OTHER = "other"                                # 其他 / 无法归类


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
