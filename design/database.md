# Database

## 核心表清单

| 表名 | 用途 |
|---|---|
| `users` | 用户账号（面试官 / 候选人） |
| `interviews` | 面试主表（一次完整面试） |
| `interview_sessions` | 面试会话（与 LangGraph State 对应） |
| `interview_messages` | 面试消息记录（问答历史） |
| `resumes` | 简历存储（文本 + 解析结果） |
| `job_descriptions` | JD 存储 |
| `questions` | 题目库 |
| `answers` | 候选人回答记录 |
| `evaluations` | 评分记录（每题评分） |
| `reports` | 最终面试报告 |
| `agent_traces` | Agent 执行 Trace 记录（Observability） |
| `sandbox_runs` | Sandbox 代码执行记录 |
| `files` | 文件元数据（简历 PDF / 音频 / 图片） |

---

## 核心关联关系

```text
users
  └── interviews (user_id)
        └── interview_sessions (interview_id)
              └── interview_messages (session_id)

interviews
  ├── resumes (interview_id)
  ├── job_descriptions (interview_id)
  ├── questions (interview_id)
  ├── answers (question_id)
  ├── evaluations (answer_id)
  └── reports (interview_id)

agent_traces → interview_sessions (session_id)
sandbox_runs → answers (answer_id)
files → resumes / answers (polymorphic)
```

---

## 关键字段说明

### interviews
- `status`: pending / in_progress / completed / cancelled
- `stage`: introduction / resume / basic / project / system_design / behavior / summary

### interview_sessions
- `graph_state`: JSON，存储 LangGraph InterviewState 快照

### evaluations
- `technical_score`: float (0-100)
- `engineering_score`: float (0-100)
- `architecture_score`: float (0-100)
- `communication_score`: float (0-100)
- `overall_score`: float (0-100)

### agent_traces
- `span_name`: resume_agent / question_agent / evaluation_agent / report_agent
- `latency_ms`: int
- `token_usage`: JSON
- `cost_usd`: float
