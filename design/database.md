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
| `resume_facts` | 简历事实表（每行一条 Fact，可追溯 Evidence/Confidence/Section/Page） |
| `resume_sections` | 简历语义区块（按 work/education/projects/skills 切分，便于溯源） |
| `candidate_profiles` | 标准化候选人画像（身份/教育/工作/项目/技能/能力标签） |
| `jd_match_results` | JD 匹配结果（skill_match / missing_skills / risk / gap / score） |
| `job_search_plans` | 面向一份已就绪 JD 与简历的生成式求职准备计划 |
| `job_search_plan_tasks` | 计划中的 AI 或人工任务，带证据、排序和完成状态 |
| `resume_processing_runs` | 简历上传、隐私审批、重试和重解析的处理运行及安全失败诊断 |

---

## 核心关联关系

```text
users
  └── interviews (user_id)
        └── interview_sessions (interview_id)
              └── interview_messages (session_id)

interviews
  ├── resumes (interview_id)
  ├── questions (interview_id)
  ├── answers (question_id)
  ├── evaluations (answer_id)
  └── reports (interview_id)

job_descriptions（独立表；经 jd_match_results 关联 resumes）
resumes → candidate_profiles / resume_facts / resume_sections (resume_id)

agent_traces → interview_sessions (session_id)
sandbox_runs → answers (answer_id)
files → resumes / answers (polymorphic)
```

---

## 关键字段说明

### interviews
- `status`: pending / in_progress / completed / cancelled
- `stage`: introduction / resume / basic / project / system_design / behavior / summary
- `resume_id`: 可空；从简历草稿发起的面试不关联已解析简历
- `resume_snapshot`: JSONB，草稿面试出题用的脱敏内容快照（创建时经 PrivacyGuard fail-closed 校验）；存在时出题/评估优先使用快照而非简历解析结果

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

---

## Resume Intelligence Platform 扩展表（RIP-001/002/003）

### 扩展关联关系

```text
resume_sections → resumes (resume_id)
resume_facts → resumes (resume_id)
candidate_profiles → resumes (resume_id, unique)
jd_match_results → resumes (resume_id) / job_descriptions (jd_id)
job_search_plans → job_descriptions (jd_id) / resumes (resume_id) / jd_match_results (match_result_id)
job_search_plan_tasks → job_search_plans (plan_id)
```

### resume_sections（RIP-002）
- `resume_id`: FK → resumes
- `section_index`: 区块顺序
- `section_type`: work / education / projects / skills / certificates
- `title`: 区块标题
- `raw_text`: 区块原文（JSON 序列化）
- `page`: 来源页码（可空，PDF 有值）

### resume_facts（RIP-002）
- `resume_id`: FK → resumes
- `fact_type`: skill / education / work / project / certificate
- `fact_key`: 归一化键（如 "Redis"）
- `fact_value`: JSONB，结构化值
- `evidence_source_text` / `evidence_section`: 原文证据
- `evidence_page`: 来源页码（可空）
- `confidence`: float (0-1) 置信度
- `meta`: JSONB 附加元数据
- `parser_version`: 抽取器版本，支持重解析追溯

### candidate_profiles（RIP-002）
- `resume_id`: FK → resumes（唯一）
- `identity` / `education` / `work_experiences` / `projects` / `skills` / `certificates`: JSONB
- `ability_tags` / `interview_clues` / `risks`: JSONB（分类器生成）
- `parser_version`: 抽取器版本

### jd_match_results（RIP-003）
- `resume_id`: FK → resumes
- `jd_id`: FK → job_descriptions（非空；传 jd_text 时现场建 JD 后回填）
- `match_score`: float (0-100)
- `skill_match` / `missing_skills` / `risk` / `gap`: JSONB
- `recommendation`: strong_hire / hire / conditional / reject
- `detail`: 文字总结

### job_search_plans / job_search_plan_tasks（RIP-008）
- `job_search_plans` 仅引用 ready JD 和有 Candidate Profile 的简历；未完成的同一 JD+简历组合由部分唯一索引限制为一条。
- 计划以 `generation_run_id` 拒绝过期 worker 写回，以 `revision` 实施全部计划/任务 mutation 的乐观并发控制。
- `job_search_plan_tasks` 的 `basis` 保存已解析的 Source Catalog 证据；manual 任务与已完成任务在再生成中保留。

### resumes / resume_processing_runs（错误可观测性切片）
- `resumes.processing_run_id`: 当前有效 worker run 的 UUID；worker 写入前必须匹配该值。
- `resumes.processing_error_details`: 仅保存 `error_code/step/attempt/retryable/public_message` 等 allow-list 字段，不保存异常正文、prompt 或简历内容。
- `resume_processing_runs`: 每次上传、隐私审批、重试或重解析的运行历史；被新 run 取代的旧 run 以安全错误码结束，过期 run 收敛为可手动重试的失败。
- API 只返回 `run_id` 和安全诊断，Celery `task_id` 仅用于内部日志/运行记录。
