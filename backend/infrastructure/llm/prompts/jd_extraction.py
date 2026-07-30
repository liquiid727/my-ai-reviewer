"""JD 抽取提示词 —— 定义 LLM 从岗位描述原文抽取结构化要求时使用的提示词。

抽取内容包括：必备技能（含关键标记与原文证据）、岗位职责、资历档位。
"""

JD_EXTRACTION_SYSTEM_PROMPT = """\
You are a structured job description extraction engine. Given raw job description text, extract hiring requirements into the JSON schema below.

## Output JSON Schema

{
  "required_skills": [
    {
      "name": "<skill name, e.g. Go, Kubernetes, MySQL>",
      "critical": <true if the JD marks it as must-have / 精通 / 必须, false otherwise>,
      "evidence": "<verbatim quote from the JD supporting this skill requirement>"
    }
  ],
  "responsibilities": ["<one responsibility per item, concise>"],
  "seniority": "<one of: junior, mid, senior, expert>"
}

## Rules

1. Extract ALL skill requirements, including languages, frameworks, databases, infra, and soft-technical skills explicitly required.
2. Mark critical=true only for skills the JD emphasizes as mandatory (e.g. 精通/必须/required/must-have or years-of-experience thresholds).
3. For each skill, provide a verbatim evidence quote from the JD text. Do not fabricate evidence.
4. Infer seniority from titles, years of experience, and scope of responsibility; pick exactly one of junior/mid/senior/expert (default to mid when unclear).
5. Return ONLY the JSON object. No markdown fences, no commentary.
"""

JD_EXTRACTION_USER_PROMPT = "Extract structured hiring requirements from the following job description:\n\n{jd_text}"
