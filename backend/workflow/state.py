"""LangGraph 面试流程状态定义。"""

from typing import TypedDict


class QuestionItem(TypedDict):
    """面试题目项。"""

    question_id: str
    question_text: str
    stage: str
    difficulty: str
    expected_points: list[str]
    jd_relevance: str | None


class AnswerRecord(TypedDict):
    """回答评估记录。"""

    question_id: str
    answer_text: str
    is_followup: bool
    followup_round: int
    score: float
    feedback: str
    key_points_hit: list[str]
    key_points_missed: list[str]
    weight: float
    needs_followup: bool


class InterviewState(TypedDict):
    """LangGraph 面试流程的完整状态。"""

    interview_id: str
    resume_id: str
    resume_data: dict
    jd_text: str
    question_count: int

    questions: list[QuestionItem]
    current_question_index: int

    answers: list[AnswerRecord]
    current_followup_count: int
    pending_followup: str | None

    is_finished: bool

    _current_answer_text: str
    _evaluation: dict
