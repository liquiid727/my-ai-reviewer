# Roadmap

## 总开发阶段

| Phase | Feature ID | 名称 | 核心技术 | 预计时长 | 状态 |
|---|---|---|---|---|---|
| 1 | AIP-001 | MVP 文字面试 Agent | FastAPI + LangGraph | 1-2 周 | Not Started |
| 2 | AIP-002 | Workflow 升级 | Stage Router + Followup | 1 周 | Pending |
| 3 | AIP-003 | RAG 知识库 | Qdrant + Hybrid Search + Rerank | 1 周 | Pending |
| 4 | AIP-004 | Evaluation 系统 | LLM-as-Judge + Structured Output | 1 周 | Pending |
| 5 | AIP-005 | Memory 系统 | Redis Session + PostgreSQL Profile | 1 周 | Pending |
| 6 | AIP-006 | Sandbox | Docker + gVisor 代码执行 | 2 周 | Pending |
| 7 | AIP-007 | Multimodal | ASR + TTS + Vision | 2 周 | Pending |
| 8 | AIP-008 | SaaS 化 | Multi-tenant + RBAC + Billing | 3 周 | Pending |

**总预估**：约 13 周

---

## Phase 1 — MVP 文字面试 Agent

**目标**：跑通完整面试流程（文字）

验收标准：
```
上传简历 → 生成 5 个问题 → 候选人回答 → 每题评分 → 输出面试报告
```

详细规格：`specs/AIP-001-mvp-interview/spec.md`

---

## Phase 2 — Workflow 升级

**目标**：支持多阶段面试 + 动态追问

新增节点：
- `StageRouter`：按阶段路由（Resume/Basic/Project/System Design/Behavior）
- `FollowupGenerator`：根据回答生成追问
- `QuestionGenerator`：按阶段和难度生成问题

---

## Phase 3 — RAG 知识库

**目标**：从题库检索相关题目，提升出题质量

技术方案：
- Qdrant Collection：`question_bank`
- 流程：关键词召回 → 向量召回 → Rerank → Prompt → LLM

数据来源：Go / Redis / MySQL / Kubernetes / System Design 题库

---

## Phase 4 — Evaluation 系统

**目标**：多维度结构化评分

评分维度：Technical / Engineering / Architecture / Communication / Problem Solving

技术方案：LLM-as-Judge + Pydantic 结构化输出

---

## Phase 5 — Memory 系统

**目标**：跨题目、跨阶段记忆候选人状态

- 短期记忆（Redis）：当前阶段、历史问答
- 长期记忆（PostgreSQL）：技能画像、弱项画像

---

## Phase 6 — Sandbox

**目标**：支持候选人提交代码题并执行验证

支持语言：Python / Go / Java

MVP 方案：Docker 容器隔离
生产方案：gVisor / Firecracker

---

## Phase 7 — Multimodal

**目标**：支持语音面试 + 图像分析（架构图、白板）

- ASR：Whisper / SenseVoice
- TTS：OpenAI TTS / CosyVoice
- Vision：GPT-4o / Qwen-VL

---

## Phase 8 — SaaS 化

**目标**：多租户企业级部署

模块：Multi-tenant / RBAC / Billing / Quota / Audit
