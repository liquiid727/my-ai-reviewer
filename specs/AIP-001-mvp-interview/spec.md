# AIP-001 — MVP Interview Agent

**Version**: v1.0
**Status**: Not Started
**Estimated**: 1-2 周

---

## 目标

构建最小可用的文字面试 Agent，跑通完整面试闭环：

```
上传简历 → 输入 JD → 生成问题 → 候选人回答 → 评分 → 生成报告
```

不包含（留给后续 Phase）：
- RAG 题库（Phase 3）
- 动态追问（Phase 2）
- 语音 / 视觉（Phase 7）
- 代码题 Sandbox（Phase 6）

---

## 技术栈

```text
FastAPI        API 层
LangGraph      Workflow 引擎
PostgreSQL     主数据库
Redis          缓存（为 Phase 2 Memory 预留）
SQLAlchemy 2   ORM（async）
Alembic        数据库迁移
OpenAI API     LLM（默认 gpt-4o）
```

---

## 接口定义

### 简历上传
```http
POST /api/v1/resume/upload
Content-Type: multipart/form-data

Body:
  file: PDF 或 DOCX

Response:
{
  "resume_id": "uuid",
  "skills": ["Go", "Redis", "PostgreSQL"],
  "projects": [{ "name": "...", "tech": [...] }]
}
```

### 创建面试
```http
POST /api/v1/interview/create
Content-Type: application/json

Body:
{
  "resume_id": "uuid",
  "jd_text": "招聘高级后端工程师，要求...",
  "question_count": 5
}

Response:
{
  "interview_id": "uuid",
  "status": "pending"
}
```

### 开始面试
```http
POST /api/v1/interview/{id}/start

Response:
{
  "question_id": "uuid",
  "question": "请介绍一下你在上一家公司的主要技术挑战？",
  "stage": "resume"
}
```

### 提交回答
```http
POST /api/v1/interview/{id}/answer
Body:
{
  "question_id": "uuid",
  "answer": "..."
}

Response:
{
  "score": 85,
  "feedback": "回答清晰，但缺少具体数据支撑",
  "next_question": "...",        // null 表示面试结束
  "is_finished": false
}
```

### 获取报告
```http
GET /api/v1/interview/{id}/report

Response:
{
  "interview_id": "uuid",
  "overall_score": 82,
  "technical_score": 85,
  "communication_score": 78,
  "summary": "...",
  "strengths": [...],
  "improvements": [...]
}
```

---

## LangGraph Graph

```text
START
  ↓
analyze_resume      (Resume Agent: 解析技能 + 项目)
  ↓
generate_questions  (Question Agent: 基于 resume + JD 生成 N 题)
  ↓
[LOOP: 每道题]
  ↓
present_question    (向用户返回当前问题，等待回答)
  ↓
evaluate_answer     (Evaluation Agent: 评分 + feedback)
  ↓
has_more_questions? ─── Yes ──→ present_question
  ↓ No
generate_report     (Report Agent: 汇总生成最终报告)
  ↓
END
```

---

## Agent 规格

### Resume Agent
**输入**：简历文本（PDF 解析后）
**输出**：`{ skills: [], projects: [] }`
**Prompt**：提取候选人技能栈和项目经历，结构化输出 JSON

### Question Agent
**输入**：`resume_summary + jd_text + question_count`
**输出**：`[{ question: "...", stage: "basic" }, ...]`
**Prompt**：根据候选人背景和 JD 生成相关面试题，覆盖技术基础 + 项目经验

### Evaluation Agent
**输入**：`question + answer`
**输出**：`{ score: 0-100, feedback: "..." }`
**Prompt**：从技术正确性、表达清晰度评分，给出改进建议

### Report Agent
**输入**：`{ questions_and_answers: [...], evaluations: [...] }`
**输出**：完整面试报告 JSON
**Prompt**：综合所有评分，生成结构化面试报告

---

## 验收标准

```text
✓ POST /api/v1/resume/upload 能解析 PDF 简历并返回技能列表
✓ POST /api/v1/interview/create 能创建面试并关联简历
✓ POST /api/v1/interview/{id}/start 能返回第一个问题
✓ POST /api/v1/interview/{id}/answer 能评分并返回下一题
✓ 5 题回答完成后 is_finished=true
✓ GET /api/v1/interview/{id}/report 能返回最终报告
✓ 所有数据持久化到 PostgreSQL
```
