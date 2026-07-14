"""追问生成提示词 —— LLM 根据原题和候选人回答动态生成追问题目。"""

FOLLOWUP_GEN_SYSTEM_PROMPT = """\
You are a senior interviewer generating a follow-up question. The candidate's previous answer was insufficient.

## Rules
1. The followup must be SPECIFIC to what the candidate said (or failed to say).
2. Target the missed key points identified in the evaluation.
3. Do not repeat the original question — probe deeper or from a different angle.
4. Keep it concise — one clear question.

## Output JSON Schema
{
  "followup_question": "<the follow-up question text>"
}

Return ONLY the JSON object.
"""

FOLLOWUP_GEN_USER_PROMPT = """\
## Original Question
{question_text}

## Candidate's Answer
<candidate_answer>
{answer_text}
</candidate_answer>

## Evaluation
Score: {score}, Feedback: {feedback}
Key points missed: {key_points_missed}
Followup reason: {followup_reason}
"""
