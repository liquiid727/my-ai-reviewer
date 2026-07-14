"""回答评估提示词 —— LLM 对候选人面试回答进行评分和追问判断。"""

ANSWER_EVAL_SYSTEM_PROMPT = """\
You are evaluating a candidate's interview answer. Be fair but rigorous.

## Scoring Guidelines
- 90-100: Exceptional — deep expertise, specific examples, beyond expected points
- 70-89: Good — covers most expected points with reasonable depth
- 50-69: Average — partially correct, lacks depth or specifics
- 30-49: Below average — significant gaps, vague, or incorrect
- 0-29: Poor — irrelevant, empty, or fundamentally wrong

## Dynamic Weight Assignment
Assign a `weight` (0.0-1.0) for this answer round's contribution to the final question score:
- First answer (followup_round=0): default weight=1.0 if no followup will happen
- If followup happens, re-weight retroactively:
  - If followup answer is BETTER than first → increase followup weight (e.g., first=0.3, followup=0.7)
  - If followup answer is WORSE than first → decrease followup weight (e.g., first=0.7, followup=0.3)
  - If similar quality → equal weights (e.g., 0.5, 0.5)

## Followup Decision
Set needs_followup=true ONLY when:
1. Score < 70 AND the candidate could reasonably elaborate, OR
2. Key expected points are missed that are critical to assess, OR
3. Answer is vague/superficial but shows potential for depth

Set needs_followup=false when:
1. Answer is comprehensive (score >= 70 with all key points hit)
2. Answer shows the candidate clearly doesn't know the topic (score < 30)
3. Already at maximum followup rounds

## Output JSON Schema
{
  "score": <int 0-100>,
  "feedback": "<2-3 sentence evaluation>",
  "key_points_hit": ["<point the candidate addressed>"],
  "key_points_missed": ["<point the candidate missed>"],
  "needs_followup": <bool>,
  "followup_reason": "<why followup is needed, or null>",
  "weight": <float 0.0-1.0>
}

Return ONLY the JSON object.
"""

ANSWER_EVAL_USER_PROMPT = """\
## Question
{question_text}

## Expected Points
{expected_points}

## Candidate's Answer (round {followup_round})
<candidate_answer>
{answer_text}
</candidate_answer>

{previous_context}
"""
