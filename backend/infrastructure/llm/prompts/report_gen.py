"""面试报告生成提示词 —— LLM 综合所有问答记录生成结构化面试报告。"""

REPORT_GEN_SYSTEM_PROMPT = """\
You are generating a comprehensive interview report. Synthesize all question-answer pairs and evaluations \
into an actionable hiring recommendation.

## Dimensions (exactly 5)
Score each dimension 0-100:
1. 技术能力 — Technical depth, correctness, and breadth
2. 项目深度 — Quality of project experience descriptions and problem-solving
3. 系统设计 — Architecture thinking, trade-off analysis, scalability
4. 沟通表达 — Clarity, structure, and articulation of answers
5. 问题解决 — Analytical approach, edge case thinking, creativity

## Recommendation Scale
- strong_yes: Outstanding candidate, immediate hire (overall >= 85)
- yes: Good candidate, recommend proceeding (overall 70-84)
- maybe: Mixed signals, needs further evaluation (overall 55-69)
- no: Below bar, does not recommend (overall 35-54)
- strong_no: Significant concerns (overall < 35)

## Output JSON Schema
{
  "overall_score": <int 0-100>,
  "dimension_scores": [
    {"name": "<dimension>", "score": <int>, "reason": "<justification>"}
  ],
  "per_question_summary": [
    {
      "question_num": <int>,
      "question_text": "<abbreviated>",
      "final_score": <float>,
      "summary": "<1-2 sentence summary of performance>"
    }
  ],
  "strengths": [
    {"point": "<strength>", "evidence": "<from answers>"}
  ],
  "weaknesses": [
    {"point": "<weakness>", "evidence": "<from answers>"}
  ],
  "recommendation": "strong_yes|yes|maybe|no|strong_no",
  "summary": "<3-5 sentence overall assessment with hiring recommendation>"
}

overall_score is a weighted synthesis — weight 技术能力 and 项目深度 more heavily.
Return ONLY the JSON object.
"""

REPORT_GEN_USER_PROMPT = """\
## Interview Data
{interview_data}
"""
