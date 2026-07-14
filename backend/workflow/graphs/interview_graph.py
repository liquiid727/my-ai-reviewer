"""LangGraph 面试流程图 —— 编排面试问答全流程。"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.workflow.checkpointer import get_checkpointer
from backend.workflow.nodes.analyze_resume import analyze_resume
from backend.workflow.nodes.decide_next import (
    decide_next,
    finish_interview,
    generate_followup,
    next_question,
)
from backend.workflow.nodes.evaluate_answer import evaluate_answer
from backend.workflow.nodes.generate_questions import generate_questions
from backend.workflow.nodes.present_question import present_question
from backend.workflow.state import InterviewState


def build_interview_graph() -> StateGraph:
    """构建面试流程的 StateGraph（不含 checkpointer）。"""
    builder = StateGraph(InterviewState)

    builder.add_node("analyze_resume", analyze_resume)
    builder.add_node("generate_questions", generate_questions)
    builder.add_node("present_question", present_question)
    builder.add_node("evaluate_answer", evaluate_answer)
    builder.add_node("generate_followup", generate_followup)
    builder.add_node("next_question", next_question)
    builder.add_node("finish", finish_interview)

    builder.add_edge(START, "analyze_resume")
    builder.add_edge("analyze_resume", "generate_questions")
    builder.add_edge("generate_questions", "present_question")
    builder.add_edge("present_question", "evaluate_answer")
    builder.add_conditional_edges(
        "evaluate_answer",
        decide_next,
        {
            "generate_followup": "generate_followup",
            "next_question": "next_question",
            "finish": "finish",
        },
    )
    builder.add_edge("generate_followup", "present_question")
    builder.add_edge("next_question", "present_question")
    builder.add_edge("finish", END)

    return builder


async def get_compiled_graph() -> CompiledStateGraph:
    """获取编译后的面试流程图（含 PostgreSQL checkpointer）。"""
    builder = build_interview_graph()
    checkpointer = await get_checkpointer()
    return builder.compile(checkpointer=checkpointer)
