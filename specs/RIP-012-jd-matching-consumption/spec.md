# RIP-012 JD Matching Consumption and Freshness

## 1. Meta

- **Spec ID:** RIP-012
- **Title:** JD Matching Consumption and Freshness
- **Epic:** Resume Intelligence Platform
- **Status:** Proposed
- **Owner Agent:** Frontend Agent + Backend Agent + QA Agent
- **Depends On:** RIP-008, RIP-011
- **Prerequisites:** ready `hybrid_v2` match API, existing JD Detail, Job Search Plan and Interview compatibility paths
- **PRD:** `spec-draft/jd-intelligence-v2-2026-08-05.md` (US-008~US-010; FR-23~FR-30)
- **Baseline:** `main` at `8c05329`; generated 2026-08-05 from a dirty worktree without modifying existing application code

## 2. Goal

让用户在 JD 详情页理解并重新计算多维匹配结果，并让求职计划与面试链路只消费与当前 JD、候选事实和匹配器版本一致的结果，同时通过端到端证据关闭 PRD/SPEC/实现漂移。

## 3. Why This Exists

当前前端触发 `/jd/match` 后主要显示成功提示，没有完整匹配结果视图。RIP-008 的 match freshness 只比较 `created_at` 与 JD/Profile `updated_at`，无法识别 Facts、Prompt、schema、matcher 或 model 变化。Interview 主要接收自由文本 `jd_text`，没有稳定的 `jd_id`/`match_result_id` 引用。

如果只完成 RIP-011 后端而不更新这些消费者，旧结果仍可能被展示或用于生成计划/问题，PRD 与下游 SPEC 会继续漂移。

## 4. Out of Scope

- 不实现候选人批量排名、自动淘汰、通知或 ATS 集成。
- 不替换 RIP-008 的计划生命周期、任务编辑、revision 或 regenerate 原子性。
- 不移除 Interview 的 `jd_text` 兼容输入。
- 不设计跨租户权限、分享链接或导出完整匹配报告。
- 不提供任意 Prompt、模型或权重调试控制台。

## 5. Deliverables

- JD Detail 中的匹配选择、异步状态、结果解释、历史和 recompute UI。
- typed frontend API/types 与统一错误/轮询处理。
- 可复用 freshness policy，供 matching、Plan 和 Interview 调用。
- RIP-008 Source Catalog/input snapshot 对 `hybrid_v2` 版本字段的兼容升级。
- Interview 可选 `jd_id`/`match_result_id` 和不可变上下文快照。
- 合成数据端到端场景、浏览器证据和文档 closeout。

## 6. Domain

### 6.1 Consumer Freshness Decision

消费者不得只用时间戳比较。统一结果：

```text
fresh: stored input_fingerprint == fingerprint(current inputs + required matcher policy)
stale: mismatch with one or more stable reason codes
unusable: status != ready OR privacy/ownership/resource validation failed
```

稳定 stale reason 至少包括：

- `jd_revision_changed`
- `resume_facts_revision_changed`
- `profile_revision_changed`
- `matcher_version_changed`
- `hard_filter_policy_changed`
- `prompt_or_schema_changed`
- `model_changed`
- `result_failed_or_incomplete`

旧结果保持历史可读；消费者必须显式选择 recompute、降级 `rules_v1` 或停止。不得静默把 stale `hybrid_v2` 当成 fresh。

### 6.2 Presentation States

前端状态：`empty/loading/queued/running/ready/failed/stale/recompute_pending/timed_out`。hard filter `fail`、`unknown` 与 dimension `conflict/unknown` 必须使用不同标签和说明。

匹配结果属于招聘辅助信息。页面必须显示模型分析免责声明、证据覆盖率和人工确认提示，不能把 recommendation 显示成自动录用结论。

## 7. Application

### 7.1 JD Detail

1. 选择具有 Candidate Profile 的简历。
2. 查询该 JD/resume 最新 `hybrid_v2` 结果。
3. 没有结果时允许创建；queued/running 时轮询；ready 时展示；stale 时显示原因和 recompute。
4. 轮询在终态、超时、页面隐藏、卸载或资源切换时停止。
5. recompute 复用活动 run，避免重复请求。

### 7.2 Job Search Plan

- `get_fresh_match` 使用统一 fingerprint/freshness policy。
- Plan generation snapshot 保存 `match_result_id`、mode、input fingerprint、matcher/policy/prompt/schema/provider/model 和 dimension摘要。
- 创建或 regenerate 时若无 fresh `hybrid_v2`，按产品策略触发 recompute 并等待终态；不可用时安全失败，不静默复用旧结果。
- 已生成计划在输入变化后显示 stale，但历史任务仍可读；用户显式 regenerate 才替换 AI 任务。
- 保持 RIP-008 的 revision、run id、manual/done task preservation 和原子替换契约。

### 7.3 Interview

- 创建请求可选新增 `jd_id` 和 `match_result_id`；旧 `jd_text` 继续有效。
- 提供 `match_result_id` 时必须属于同一 resume/JD 且为 ready；若 stale，则返回明确错误或要求 recompute。
- 面试创建时保存最小化 JD structured snapshot 和 dimension/gap evidence 摘要；后续 JD/match 修改不改变已开始面试的上下文。
- 进入 LLM 的候选内容继续通过 RIP-009 fail-closed privacy guard。

### 7.4 Traceability Closeout

每个 issue 完成时更新对应 `tasks.md`、`current/`、设计文档、测试计划和结果。最终验收必须对照 PRD FR -> Spec section -> issue -> code -> test -> evidence 生成矩阵。

## 8. Repository

建议实现位置：

```text
frontend/src/api/jd.ts                         [MODIFY: typed v2 match APIs]
frontend/src/types/jd.ts                       [MODIFY]
frontend/src/components/jd/MatchResultPanel.tsx [NEW]
frontend/src/pages/JDDetailPage.tsx            [MODIFY]
backend/application/jd_matching/freshness.py   [REUSE/EXTEND]
backend/application/plan_service.py             [MODIFY]
backend/tasks/plan_tasks.py                     [MODIFY]
backend/api/v1/interview.py                     [MODIFY]
backend/application/interview_service.py        [MODIFY]
backend/infrastructure/db/models.py              [MODIFY]
infra/alembic/versions/<revision>_match_consumers.py [NEW if interview snapshot columns are required]
tests/plans/RIP-012-jd-matching-consumption.md   [NEW]
```

当前 `backend/tasks/plan_tasks.py` 和 `backend/tasks/interview_tasks.py` 在本 SPEC 生成时已有未提交修改；实现者必须先检查并保留这些用户改动。

## 9. API

### 9.1 Frontend Consumption

使用 RIP-011 的创建、详情、历史和 recompute API。前端类型必须覆盖 nullable score、hard filter、dimension evidence、coverage/confidence、version 和 stale reasons；不得再把 match response 简化为仅 `{id}`。

### 9.2 Plan Compatibility

现有 `POST /api/v1/plans`、retry、regenerate、detail 和 task mutation 契约不改变。详情增量返回：

```json
{
  "match": {
    "id": "uuid",
    "mode": "hybrid_v2",
    "input_fingerprint": "sha256",
    "fresh": true,
    "stale_reasons": []
  }
}
```

### 9.3 Interview Compatibility

现有 resume/draft 二选一规则保持不变：

```json
{
  "resume_id": "uuid",
  "draft_id": null,
  "jd_text": null,
  "jd_id": "uuid",
  "match_result_id": "uuid"
}
```

`jd_text`、`jd_id` 至少提供其一；`match_result_id` 必须伴随 `jd_id`。旧只传 `jd_text` 的客户端继续工作。

## 10. Database Impact

优先复用 RIP-011 的 immutable `input_snapshot` 和 RIP-008 的 `match_result_id/input_snapshot`，避免重复保存完整数据。

如现有 Interview 模型没有可审计快照位置，则增量新增：

- `jd_id UUID NULL FK job_descriptions ON DELETE SET NULL`
- `match_result_id UUID NULL FK jd_match_results ON DELETE SET NULL`
- `jd_context_snapshot JSONB NULL`
- `match_context_snapshot JSONB NULL`
- `context_fingerprint CHAR(64) NULL`

迁移对历史面试全部保持 null，旧读取不受影响。快照只保存最小化、已脱敏内容，不保存原始简历或完整 JD 图片。

## 11. Test Plan

- Frontend component：所有结果/硬条件/维度/证据/错误/stale/recompute 状态。
- Browser：桌面和移动端从图片 JD ready 到匹配 ready、查看证据、修改 JD、stale、recompute。
- Freshness unit：每个 reason 单独变化、多个变化、模型/Prompt/schema/matcher 变化。
- Plan integration：fresh 复用、stale recompute、failed 不生成、snapshot 版本、regenerate 保留人工与 done 任务。
- Interview integration：旧 `jd_text`、`jd_id`、`match_result_id`、跨 resume/JD 拒绝、stale 拒绝、不可变快照、privacy guard。
- Concurrency：旧 match/plan/interview worker 不覆盖新 run 或 revision。
- E2E：使用合成 JD 图片和合成 masked resume facts，禁止真实 PII。
- Traceability：PRD/SPEC/issues/code/tests/evidence 无断链，未运行检查标为 NOT_RUN 或 BLOCKED。

## 12. Definition of Done

- [ ] US-008~US-010 和 FR-23~FR-30 均有自动化或浏览器证据。
- [ ] JD Detail 可完整查看和重新计算 `hybrid_v2`，并区分所有异步与不确定状态。
- [ ] Plan 与 Interview 不把 stale 或 failed match 当作 fresh 输入。
- [ ] 旧 Plan API、Interview `jd_text` 路径和 `rules_v1` 匹配保持兼容。
- [ ] snapshot、日志、响应、测试和截图不含原始简历或真实 PII。
- [ ] 相关 migration、lint/type/unit/integration/frontend build/browser checks 有真实状态记录。
- [ ] RIP-003/007/008/010/011/012、roadmap、issue index、current 和 as-built design 完成一致性 closeout。
