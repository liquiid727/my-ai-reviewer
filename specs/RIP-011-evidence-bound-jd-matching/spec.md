# RIP-011 Evidence-bound JD Matching

## 1. Meta

- **Spec ID:** RIP-011
- **Title:** Evidence-bound JD Matching
- **Epic:** Resume Intelligence Platform
- **Status:** Proposed
- **Owner Agent:** Backend Agent + Testing Agent
- **Depends On:** RIP-002, RIP-003, RIP-009, RIP-010
- **Prerequisites:** ready structured JD, approved masked resume facts/profile, verified text LLM configuration, `rules_v1` compatibility baseline
- **PRD:** `spec-draft/jd-intelligence-v2-2026-08-05.md` (US-005~US-007; FR-11~FR-24, FR-28, FR-30)
- **Baseline:** `main` at `8c05329`; generated 2026-08-05 from a dirty worktree without modifying existing application code

## 2. Goal

新增 `hybrid_v2` 匹配：先用确定性规则评估显式硬条件，再让 LLM 基于 JD 与已脱敏候选人事实证据完成多维分析，最终由服务端计算总分和筛选建议，并以版本化、异步、可追溯的结果持久化。

## 3. Why This Exists

当前 `rules_v1` 仅比较 Candidate Profile 的 `skills` 和 `ability_tags`，关键技能权重 70%、非关键技能 30%。职责、相关经验、职级、项目、工程/架构和领域匹配均不参与评分；缺少关键技能只影响 recommendation，并不是真正的硬筛选。

LLM 已用于简历评估和 JD 文本结构化，但尚未接入 JD-aware matching。直接让 LLM 输出一个总分会造成不可复现、无证据、难以筛选的问题，因此本 SPEC 把事实目录、硬条件、LLM 维度判断和最终聚合拆成明确契约。

## 4. Out of Scope

- 不删除或改变旧 `POST /api/v1/jd/match` 的 `rules_v1` 语义。
- 不引入 embedding、Qdrant、RAG、向量召回或候选人排序模型。
- 不把原始简历全文、identity、邮箱、电话、地址或照片发送给匹配 LLM。
- 不让 LLM 自由决定最终筛除、录用或自动触发外部动作。
- 不在本 SPEC 实现完整结果 UI、Plan 或 Interview 消费；由 RIP-012 负责。
- 不允许用户首版任意配置维度权重。

## 5. Deliverables

- 结构化 JD hard requirement 和版本/revision 契约。
- provider-independent Source Catalog，使用稳定 evidence ID。
- 纯 domain 的 hard filter 与聚合策略。
- Pydantic 约束的七维 LLM matcher 及 evidence validator。
- 版本化 `jd_match_results` 迁移与旧结果回填。
- 异步创建、状态、详情、历史与重算 API。
- run-id、fingerprint、幂等、retry 和 stale 判定。
- 隐私、幻觉证据、并发和兼容性测试。

## 6. Domain

### 6.1 Inputs

匹配输入快照由以下内容组成：

- JD：`jd_id`、structured revision、title/seniority/responsibilities/required/preferred skills/hard requirements 及其 evidence。
- Candidate：`resume_id`、masked facts revision、profile revision、skills/work/projects/education/certificates/ability tags 的必要字段和 evidence。
- Policy：matcher version、dimension weights、hard-filter policy version、schema version、prompt version。
- Model：provider、model、verified config identity；不保存 key。

候选人的 `identity` 和原始简历全文不进入快照、Catalog 或 prompt。

### 6.2 Hard Requirement

```json
{
  "id": "JD-HARD-001",
  "type": "required_skill",
  "operator": "present",
  "value": "Python",
  "evidence_id": "JD-EVIDENCE-004",
  "enforceable": true
}
```

首版可执行类型：`required_skill`、`minimum_experience_years`、`required_certificate`、`location_constraint`、`work_authorization`。只有 JD 原文明确表达且结构化 schema 可验证的条件才能 `enforceable=true`。

每条结果为：

- `pass`：候选事实有明确满足证据。
- `fail`：候选事实有明确冲突或不足证据。
- `unknown`：没有相关事实、证据模糊或无法安全判断。

`unknown` 不得自动转成 `fail`。首版任何 hard fail 都返回 `human_confirmation_required=true`，不自动删除或拒绝候选人。

### 6.3 Source Catalog

每条 prompt 证据先进入 Catalog：

```json
{
  "id": "CAND-PROJECT-003",
  "source": "resume_fact",
  "kind": "project",
  "label": "订单服务重构",
  "excerpt": "负责服务拆分与性能优化",
  "page": 2,
  "confidence": 0.92
}
```

ID 在同一 input snapshot 中稳定。LLM 输出只能引用已存在 ID；重复、未知、跨候选人或 identity evidence ID 均使输出校验失败。

### 6.4 Dimensions and Aggregation

| Dimension | Weight |
|---|---:|
| required/preferred skill fit | 30 |
| responsibility fit | 20 |
| relevant experience | 15 |
| seniority and scope | 10 |
| project evidence | 10 |
| engineering and architecture | 10 |
| domain fit | 5 |

每个维度输出 `score: 0..100|null`、`status: supported|partial|conflict|unknown`、reason、JD evidence IDs、candidate evidence IDs、confidence。

聚合规则：

1. hard filters 独立计算，不进入加权分。
2. unknown 维度不按 0 分处理；以已知维度权重归一化计算 provisional score。
3. 已知证据权重覆盖率 `<60%`、任一 enforceable hard filter 为 unknown，或校验置信度不足时，`match_score=null` 且 recommendation=`manual_review`。
4. hard fail 时 recommendation=`hard_filter_review`，并要求人工确认。
5. hard pass 且覆盖充分：`>=80 strong_match`、`>=65 match`、`>=50 conditional`、`<50 weak_match`。
6. recommendation 由纯 domain policy 产生；忽略 LLM 提供的任何自由结论字段。

### 6.5 Freshness

`input_fingerprint` 至少包含：JD structured revision/content hash、Resume facts revision、Profile revision、matcher/hard-filter/schema/prompt version、provider/model identity。任一部分变化，旧结果对新请求为 stale；历史记录不修改。

## 7. Application

### 7.1 Matching Flow

```text
create hybrid_v2 match
  -> validate ready JD + approved Candidate Profile/Facts + verified LLM
  -> compute input fingerprint
  -> reuse same ready result or active run when exact fingerprint matches
  -> persist queued result + run id
  -> build minimized Source Catalog
  -> deterministic hard filters
  -> evidence-bound LLM dimensions
  -> validate evidence IDs and schema
  -> deterministic aggregate/recommendation
  -> persist ready result if run/fingerprint still current
```

外部 LLM 调用在事务外完成。finalize 使用 run id 和 fingerprint 条件更新；旧 worker 只能 no-op。

### 7.2 Failure and Retry

- 配置、JD 状态、Candidate Profile/Facts 或隐私门禁失败时不创建可运行结果。
- timeout、429、临时网络/provider 错误最多自动重试 2 次。
- LLM JSON/schema/evidence 错误最多追加一次纠错提示；仍失败转 failed。
- failed 结果保留安全错误码、attempt 和版本信息，但不得持久化未经验证的部分评分。
- retry 创建新 run id；相同活动 run 返回既有 resource。

### 7.3 Compatibility

- `POST /api/v1/jd/match` 保持同步 `rules_v1`，继续接受 `jd_id` 或旧 inline `jd` 输入，并返回旧字段。
- 字符串数组和 `{name, critical}` 两种 `required_skills` 继续兼容。
- 旧 `jd_match_results` 回填 `mode=rules_v1/status=ready/matcher_version=rules-v1`；未知版本字段可空。
- 新接口不要求旧调用方理解异步状态或 dimension fields。

## 8. Repository

建议实现位置：

```text
backend/domain/jd/matching_v2.py                  [NEW: hard filter + aggregate policy]
backend/domain/jd/schemas.py                      [MODIFY: hard requirements/v2 result]
backend/application/jd_matching/                  [NEW: use case, catalog, freshness]
backend/infrastructure/matchers/llm_jd_matcher.py  [NEW]
backend/infrastructure/llm/prompts/jd_matching.py  [NEW]
backend/infrastructure/db/models.py                [MODIFY]
backend/api/v1/jd.py                               [MODIFY: v2 endpoints delegate to application]
backend/tasks/jd_match_tasks.py                    [NEW]
infra/alembic/versions/<revision>_jd_matching_v2.py [NEW]
```

不得让 domain 导入 ORM、LLM gateway、Celery 或 provider SDK。现有 `backend/domain/jd/policies.py` 继续作为 `rules_v1` 基线。

## 9. API

### 9.1 Create/Recompute

```http
POST /api/v1/jd/matches
{
  "jd_id": "uuid",
  "resume_id": "uuid",
  "mode": "hybrid_v2",
  "force": false
}
```

返回 `APIResponse.data`：`id/status/mode/input_fingerprint/reused`。`force=true` 只绕过 ready-result 复用，不允许并行重复活动 run。

```http
POST /api/v1/jd/matches/{match_id}/recompute
GET  /api/v1/jd/matches/{match_id}
GET  /api/v1/jd/{jd_id}/matches?resume_id=&status=&mode=&page=&page_size=
```

详情核心字段：

```json
{
  "status": "ready",
  "mode": "hybrid_v2",
  "match_score": 78.4,
  "recommendation": "match",
  "human_confirmation_required": false,
  "hard_filters": [],
  "dimension_scores": [],
  "evidence": [],
  "coverage": 0.9,
  "confidence": 0.84,
  "matcher_version": "hybrid-v2.0",
  "prompt_version": "jd-match-v2",
  "schema_version": "2",
  "model": {"provider":"openai","name":"configured-model"},
  "input_fingerprint": "sha256",
  "stale": false,
  "stale_reasons": []
}
```

### 9.2 Errors

使用统一 envelope：1001 输入/schema，1002 资源不存在，1003 状态/run 冲突，428 LLM 不可用，5001 LLM/校验失败，5002 task timeout，5004 dispatch 失败。message 必须安全；provider body、prompt 和简历内容不得返回。

## 10. Database Impact

扩展 `job_descriptions`：

- `structured_revision integer NOT NULL DEFAULT 1`
- `hard_requirements JSONB NOT NULL DEFAULT '[]'`
- hard-requirement extraction schema/prompt version metadata

扩展 `jd_match_results`：

| Column | Type | Purpose |
|---|---|---|
| status | varchar(20) | queued/running/ready/failed/stale |
| mode | varchar(20) | rules_v1/hybrid_v2 |
| processing_run_id | UUID nullable | stale worker guard |
| input_fingerprint | char(64) nullable | idempotency/freshness |
| input_snapshot | JSONB nullable | minimized immutable inputs/catalog |
| hard_filters | JSONB | pass/fail/unknown details |
| dimension_scores | JSONB | seven dimensions |
| evidence | JSONB | bounded result evidence |
| coverage/confidence | float nullable | uncertainty |
| matcher/policy/prompt/schema_version | varchar | reproducibility |
| provider/model_name | varchar nullable | model identity |
| failure_code | varchar nullable | safe key |
| attempt | int | retry count |
| started_at/completed_at/updated_at | timestamptz | lifecycle |

新增部分唯一索引，约束同一 `jd_id/resume_id/mode/input_fingerprint` 最多一个 ready 结果和一个活动 run。迁移回填旧行并保持旧字段非空语义；不删除 `skill_match/missing_skills/risk/gap/detail`。

## 11. Test Plan

- Domain：hard filter pass/fail/unknown；技能别名；覆盖率；阈值；LLM recommendation 被忽略。
- Catalog：稳定 ID、最小化、identity 排除、unknown/duplicate/cross-input evidence 拒绝。
- Matcher：七维正常、unknown、冲突、幻觉 ID、非法 JSON、越界、纠错后失败。
- Privacy：LLM spy 断言只接收 approved masked facts/profile，无 raw resume 或 identity。
- Migration：旧结果回填、约束、索引、兼容读取。
- Application：fingerprint 复用、force、retry、timeout、failed 不产生部分 ready、stale worker no-op。
- API：旧 `/jd/match` 回归；新创建、详情、历史、重算及全部业务错误。
- Freshness：JD edit/reextract、resume reparse、facts/profile rebuild、matcher/prompt/schema/model change。

## 12. Definition of Done

- [ ] US-005~US-007 和 FR-11~FR-24、FR-28、FR-30 均映射到测试。
- [ ] 每个 LLM 维度结论都引用有效 Catalog evidence，无法引用时为 unknown 或整次失败。
- [ ] hard fail、unknown 和软评分在领域、数据库和 API 中均可区分。
- [ ] recommendation 完全由确定性 policy 计算并要求适当人工确认。
- [ ] 原始简历和 identity 未进入 prompt、snapshot、日志或错误。
- [ ] `rules_v1` API、字段和旧数据保持兼容。
- [ ] 迁移、相关静态检查、单元/集成/并发/隐私测试记录真实结果。
- [ ] as-built spec、tasks、roadmap、design/database/API 文档同步。
