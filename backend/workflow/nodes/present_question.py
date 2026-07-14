"""present_question 节点 —— 中断图执行，等待用户回答。"""

from langgraph.types import interrupt

from backend.workflow.state import InterviewState


def present_question(state: InterviewState) -> dict:
    """中断执行，将当前题目信息返回给前端，等待用户提交回答。"""
    idx = state["current_question_index"]
    question = state["questions"][idx]
    followup = state.get("pending_followup")

    if followup:
        answer_text = interrupt(
            {
                "type": "followup",
                "followup_question": followup,
                "followup_round": state["current_followup_count"],
                "question": question,
                "current_num": idx + 1,
                "total_count": len(state["questions"]),
            }
        )
    else:
        answer_text = interrupt(
            {
                "type": "question",
                "question": question,
                "current_num": idx + 1,
                "total_count": len(state["questions"]),
            }
        )

    return {"_current_answer_text": answer_text}
