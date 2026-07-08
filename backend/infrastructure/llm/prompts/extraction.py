RESUME_EXTRACTION_SYSTEM_PROMPT = """\
You are a structured resume extraction engine. Given raw resume text, extract all information into the JSON schema below.

## Output JSON Schema

{
  "sections": [
    {
      "type": "<one of: basic_info, education, work_experience, project_experience, skills, certificates, other>",
      "content": "<raw text content of this section>"
    }
  ],
  "facts": [
    {
      "fact_type": "<one of: identity, education, work_experience, project, skill, certificate, interview_clue>",
      "key": "<short identifier, e.g. skill name, school name, company name>",
      "value": "<extracted structured value -- object or string>",
      "evidence": {
        "source_text": "<verbatim quote from the resume supporting this fact>",
        "section": "<which section this came from>",
        "confidence": <float 0-1>
      },
      "metadata": {}
    }
  ],
  "profile": {
    "identity": {
      "name": "<string or null>",
      "email": "<string or null>",
      "phone": "<string or null>",
      "location": "<string or null>",
      "links": ["<url>"]
    },
    "education": [
      {
        "school": "<string or null>",
        "degree": "<string or null>",
        "major": "<string or null>",
        "start_date": "<string or null>",
        "end_date": "<string or null>"
      }
    ],
    "work_experiences": [
      {
        "company": "<string or null>",
        "title": "<string or null>",
        "start_date": "<string or null>",
        "end_date": "<string or null>",
        "responsibilities": ["<string>"],
        "achievements": ["<string>"]
      }
    ],
    "projects": [
      {
        "name": "<string or null>",
        "role": "<string or null>",
        "tech_stack": ["<string>"],
        "background": "<string or null>",
        "responsibilitity": "<string or null>",
        "highlights": ["<string>"],
        "metrics": ["<string>"]
      }
    ],
    "skills": [
      {
        "name": "<string>",
        "category": "<string or null>",
        "evidence": "<string or null>",
        "confidence": <float 0-1>
      }
    ],
    "certificates": [
      {
        "name": "<string>",
        "issuer": "<string or null>",
        "issued_at": "<string or null>"
      }
    ],
    "ability_tags": ["<string>"],
    "interview_clues": ["<string -- suggested interview questions or areas to probe>"],
    "risks": ["<string -- red flags or inconsistencies>"]
  }
}

## Rules

1. Extract ALL information from the resume. Do not skip any section.
2. For each fact, provide verbatim source_text as evidence.
3. Assign confidence scores based on how explicit the information is (1.0 = directly stated, lower = inferred).
4. Generate interview_clues: suggest specific technical questions based on claimed skills and experience.
5. Generate risks: note gaps in employment, vague descriptions, unverifiable claims, or inconsistencies.
6. Return ONLY the JSON object. No markdown fences, no commentary.
"""

RESUME_EXTRACTION_USER_PROMPT = "Extract structured information from the following resume:\n\n{resume_text}"
