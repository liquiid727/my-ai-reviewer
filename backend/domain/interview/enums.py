"""面试领域枚举 —— 定义面试流程各阶段的状态和分类标签。"""

from enum import Enum


class InterviewStatus(str, Enum):
    """面试会话状态机。"""

    PENDING = "pending"
    GENERATING = "generating"
    IN_PROGRESS = "in_progress"
    REPORT_GENERATING = "report_generating"
    COMPLETED = "completed"
    FAILED = "failed"


class QuestionStage(str, Enum):
    """面试题目考察阶段。"""

    BASIC = "basic"
    PROJECT = "project"
    ARCHITECTURE = "architecture"
    BEHAVIOR = "behavior"


class Difficulty(str, Enum):
    """题目难度等级。"""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Recommendation(str, Enum):
    """面试录用建议等级。"""

    STRONG_YES = "strong_yes"
    YES = "yes"
    MAYBE = "maybe"
    NO = "no"
    STRONG_NO = "strong_no"
