# SPEC: RIP-008 AI 求职计划列表

> Technical specification derived from: `tasks/prd-job-search-plans.md`
> Generated: 2026-08-03 | Target branch: `main` | Base commit: `ef809e6` (dirty worktree)
> Status: Approved

## 1. Summary

### 1.1 What This SPEC Covers

本 SPEC 定义独立的求职计划领域：用户选择一个 ready JD 和一份具有 Candidate Profile 的简历后，系统复用或刷新 JD Match Result，通过 Celery 异步调用 LLM 生成可追溯的综合计划。计划与任务持久化，支持列表、详情、人工编辑、自动保存、状态与进度、失败重试和保留用户工作的安全重新生成。

### 1.2 PRD Reference

- Source: `tasks/prd-job-search-plans.md`
- User Stories: US-001 ~ US-007
- Functional Requirements: FR-1 ~ FR-23
- Upstream dependency: RIP-007 ready JD list/detail contract
- Post-MVP items: TODO-PLAN-001 ~ TODO-PLAN-008，不进入本 SPEC 的实施 Issues

### 1.3 Design Decisions Summary

| Decision | Choice | Rationale |
|---|---|---|
| Domain boundary | 新建 `domain/job_search_plan` | 计划有独立生命周期，不污染 JD、Resume 或 Interview |
| Persistence | `job_search_plans` + `job_search_plan_tasks` | 支持任务级编辑、排序、查询和级联删除 |
| Generation | Celery worker + structured LLM output | 避免长请求，与已有异步模式一致 |
| Evidence contract | 服务端 Source Catalog + LLM 返回 `basis_ids` | 防止模型虚构证据路径，使建议可验证 |
| Match reuse | 仅复用不早于 JD/Profile 更新时间的最新 match | 输入更新后避免使用陈旧差距 |
| Scheduling | LLM 输出相对天数，服务端生成实际日期 | 避免模型日期计算错误并统一边界 |
| Default horizon | 未填目标日期时使用 28 天；未填每周时间时使用 8 小时 | 保证生成结果仍具有可执行节奏 |
| Duplicate plans | 同一 JD + Resume 只能有一个未完成计划 | 避免重复活跃计划；完成后允许创建新计划 |
| Concurrency | 计划级递增 `revision` | 防止自动保存、排序和多标签页互相覆盖 |
| Regeneration | 事务替换未完成 AI 任务 | 保留 done 与 manual 任务，失败不产生半更新 |
| Ownership | `user_id` 可空，匿名单用户 MVP | 与 RIP-007 一致，为鉴权预留 |
| Progress | `done / all active tasks`，按数量计算 | 符合 PRD MVP 假设，后续权重另行演进 |

## 2. Architecture

### 2.1 System Context

```text
Plan List / Create / Detail UI
            |
            v
FastAPI /api/v1/plans
            |-- validate ready JD
            |-- validate CandidateProfile
            |-- create generating plan
            |-- dispatch Celery
            v
Plan Generation Worker
            |-- load sanitized JD/Profile inputs
            |-- reuse or compute JDMatchResult
            |-- build Source Catalog
            |-- LLM structured generation
            |-- validate categories/basis/dates
            |-- atomically persist tasks
            v
PostgreSQL plans + tasks
```

### 2.2 Component Design

| Component | Responsibility |
|---|---|
| `PlanService` | 创建、查询、状态、进度、输入校验、删除 |
| `PlanTaskService` | 任务 CRUD、排序、revision 并发控制、自动完成状态 |
| `PlanGenerationService` | 匹配复用、Source Catalog、LLM 调用、输出校验与日期归一化 |
| `PlanRegenerationService` | 生成 staging 任务并事务替换可替换任务 |
| `plan_tasks` Celery module | initial generation、retry、regenerate worker entry |
| Plans API | 计划/任务 REST contract 与错误封装 |
| Plans frontend | 列表、创建、轮询、任务执行、自动保存、重新生成 |

### 2.3 Generation Flow

1. API 校验 LLM ready、JD ready、Resume 与 Candidate Profile 存在。
2. 通过 partial unique constraint 检查同组合未完成计划。
3. 创建 `status=generating`、`generation_run_id=<uuid>` 的计划并派发 Celery。
4. Worker 加载 JD、Profile；查询最新 match。
5. 若 `match.created_at < max(jd.updated_at, profile.updated_at)` 或无 match，调用现有 `JDMatchingService` 新建 match。
6. 服务端把允许使用的输入编成 Source Catalog。
7. Worker 通过 `get_active_verified_config(session)` 取得数据库中的 active verified LLM 配置，并以 `LLMGateway.from_config` 构建生成器；不得退回环境变量默认模型。
8. LLM 只输出任务内容与 `basis_ids`；Pydantic 验证后由服务端解析 evidence 和 due date。
9. 同一事务插入任务、保存去敏输入快照、设置 `active/generated_at` 并递增 revision。

### 2.4 Source Catalog

Catalog 仅包含计划生成所需信息，并为每一项生成稳定 ID：

```json
[
  {"id":"JD-SKILL-001","source":"jd","label":"Kubernetes","excerpt":"熟悉 Kubernetes"},
  {"id":"PROFILE-SKILL-001","source":"profile","label":"Go","excerpt":"Go: proficient"},
  {"id":"MATCH-GAP-001","source":"match","label":"云原生差距","excerpt":"缺少 Kubernetes 证据"},
  {"id":"PREF-WEEKLY-001","source":"preference","label":"每周可投入时间","excerpt":"8 小时"}
]
```

- Candidate Profile 的姓名、邮箱、电话、地址不进入 Catalog。
- target date、weekly hours 和 supplemental background 以 `PREF-*` 条目进入 Catalog，使投递节奏类任务也有合法依据。
- prompt 明确输入为不可信数据，正文中的指令不得改变系统任务。
- LLM 返回的 `basis_ids` 必须全部存在；未知 ID 导致输出校验失败。

### 2.5 File Structure

```text
backend/
├── api/v1/plans.py                               [NEW]
├── api/v1/resume.py                              [MODIFY: eligible resume list]
├── api/v1/router.py                              [MODIFY: include plans]
├── celery_app.py                                 [MODIFY: include plan_tasks]
├── domain/job_search_plan/
│   ├── __init__.py                               [NEW]
│   ├── enums.py                                  [NEW]
│   ├── schemas.py                                [NEW]
│   └── services.py                               [NEW]
├── infrastructure/db/models.py                   [MODIFY]
├── infrastructure/llm/prompts/plan_generation.py [NEW]
├── infrastructure/planners/
│   ├── __init__.py                               [NEW]
│   └── llm_plan_generator.py                     [NEW]
├── tasks/plan_tasks.py                           [NEW]
└── tests/
    ├── unit/test_plan_generation.py               [NEW]
    ├── unit/test_plan_services.py                 [NEW]
    ├── unit/test_plan_regeneration.py             [NEW]
    └── integration/test_plans_api.py              [NEW]

frontend/src/
├── App.tsx                                       [MODIFY: /plans routes]
├── api/plans.ts                                  [NEW]
├── components/Layout.tsx                         [MODIFY: Plan navigation]
├── components/plans/
│   ├── PlanStatusBadge.tsx                       [NEW]
│   ├── PlanTaskEditor.tsx                        [NEW]
│   ├── PlanTaskList.tsx                          [NEW]
│   └── RegeneratePlanDialog.tsx                  [NEW]
├── i18n/locales/en.ts                            [MODIFY]
├── i18n/locales/zh.ts                            [MODIFY]
├── pages/PlanCreatePage.tsx                      [NEW]
├── pages/PlanDetailPage.tsx                      [NEW]
├── pages/PlanListPage.tsx                        [NEW]
└── types/plans.ts                                [NEW]

infra/alembic/versions/<revision>_add_job_search_plans.py [NEW]
design/database.md                                [MODIFY]
design/domain.md                                  [MODIFY]
```

## 3. Data Model

### 3.1 `job_search_plans`

| Column | Type | Null | Default | Purpose |
|---|---|---:|---|---|
| `id` | UUID PK | no | uuid4 | plan id |
| `user_id` | UUID FK users | yes | null | future ownership |
| `jd_id` | UUID FK job_descriptions | no | - | one target JD |
| `resume_id` | UUID FK resumes | no | - | one candidate resume |
| `match_result_id` | UUID FK jd_match_results | yes | null | generation match reference |
| `title` | varchar(200) | no | derived | editable plan title |
| `status` | varchar(30) | no | `generating` | lifecycle |
| `target_date` | date | yes | null | user preference |
| `weekly_hours` | smallint | yes | null | 1~80 |
| `supplemental_background` | text | yes | null | max 10000 chars |
| `input_snapshot` | JSONB | no | `{}` | sanitized generation inputs |
| `llm_model` | varchar(100) | yes | null | generator model |
| `generation_run_id` | UUID | yes | null | stale worker guard |
| `generation_error` | text | yes | null | safe user error |
| `generated_at` | timestamptz | yes | null | stale input detection |
| `revision` | integer | no | 0 | optimistic concurrency |
| `created_at` | timestamptz | no | now | audit |
| `updated_at` | timestamptz | no | now | list sort |

Status values: `generating`, `regenerating`, `active`, `completed`, `failed`。

### 3.2 `job_search_plan_tasks`

| Column | Type | Null | Default | Purpose |
|---|---|---:|---|---|
| `id` | UUID PK | no | uuid4 | task id |
| `plan_id` | UUID FK plans | no | - | owning plan |
| `title` | varchar(300) | no | - | action title |
| `category` | varchar(40) | no | - | six-category taxonomy |
| `description` | text | no | `''` | concrete action |
| `basis` | JSONB | no | `[]` | resolved evidence list |
| `source` | varchar(20) | no | `manual` | `ai/manual` |
| `priority` | varchar(20) | no | `medium` | `high/medium/low` |
| `status` | varchar(20) | no | `todo` | `todo/in_progress/done` |
| `due_date` | date | yes | null | normalized deadline |
| `sort_order` | integer | no | 0 | stable ordering |
| `created_at` | timestamptz | no | now | audit |
| `updated_at` | timestamptz | no | now | edit conflict context |

Categories: `gap_priority`, `resume`, `skill`, `evidence_project`, `interview`, `application_review`。

### 3.3 Constraints and Relationships

- `plans.jd_id -> job_descriptions.id ON DELETE RESTRICT`。
- `plans.resume_id -> resumes.id ON DELETE RESTRICT`。
- `plans.match_result_id -> jd_match_results.id ON DELETE SET NULL`。
- `tasks.plan_id -> plans.id ON DELETE CASCADE`。
- Partial unique index `(jd_id,resume_id)` WHERE status IN (`generating`,`regenerating`,`active`,`failed`)。
- Index `(user_id,updated_at DESC)`、`(user_id,status)`、`(plan_id,sort_order)`、`(plan_id,status)`、`(due_date)`。
- Check constraints cover status/category/source/priority and `weekly_hours BETWEEN 1 AND 80`。
- Task hard limit: one plan最多 200 active rows；AI initial generation 6~30 tasks。

### 3.4 Generation Output Schema

```python
class GeneratedPlanTask(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    category: PlanTaskCategory
    description: str = Field(min_length=1, max_length=3000)
    priority: Literal["high", "medium", "low"]
    due_offset_days: int = Field(ge=0, le=365)
    basis_ids: list[str] = Field(min_length=1, max_length=10)

class PlanGenerationOutput(BaseModel):
    suggested_title: str = Field(min_length=1, max_length=200)
    tasks: list[GeneratedPlanTask] = Field(min_length=6, max_length=30)
```

服务端额外验证六类 category 各至少一项、basis id 全部存在、任务标题不重复。

### 3.5 Migration Plan

1. RIP-008 迁移必须依赖 RIP-007 的实际 Alembic head。
2. 创建 plans、tasks、constraints、indexes 和 partial unique index。
3. 不迁移旧数据，因为当前不存在计划持久化表。
4. downgrade 先删除 tasks，再删除 plans；不改 JD、Resume 或 Match 数据。

## 4. API Design

### 4.1 Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/plans` | 分页、搜索和状态筛选 |
| POST | `/api/v1/plans` | 创建并异步生成计划 |
| GET | `/api/v1/plans/{plan_id}` | 详情、任务、进度和生成状态 |
| PATCH | `/api/v1/plans/{plan_id}` | 修改标题和生成偏好 |
| DELETE | `/api/v1/plans/{plan_id}` | 删除计划及任务 |
| POST | `/api/v1/plans/{plan_id}/retry` | 重试首次生成失败 |
| POST | `/api/v1/plans/{plan_id}/regenerate` | 安全重新生成 AI 任务 |
| POST | `/api/v1/plans/{plan_id}/tasks` | 新增 manual 任务 |
| PATCH | `/api/v1/plans/{plan_id}/tasks/{task_id}` | 编辑单任务 |
| DELETE | `/api/v1/plans/{plan_id}/tasks/{task_id}` | 删除非 done 任务 |
| PUT | `/api/v1/plans/{plan_id}/tasks/order` | 批量更新任务顺序 |
| GET | `/api/v1/resume` | 分页列出有 Candidate Profile 的简历选项 |

### 4.2 Create Request

```json
{
  "jd_id": "uuid",
  "resume_id": "uuid",
  "title": null,
  "target_date": "2026-09-01",
  "weekly_hours": 8,
  "supplemental_background": "每周工作日晚间可准备"
}
```

- `title` 为空时使用“{company} - {job title} 求职计划”，缺失公司时只使用岗位名。
- `target_date` 必须是今天或之后，最长 365 天。
- `weekly_hours` 为空时生成使用 8，但数据库仍保留 null，以区分用户设置与默认值。
- supplemental background trim 后最多 10000 字符，并作为不可信输入处理。

Create response immediately returns:

```json
{
  "id": "uuid",
  "status": "generating",
  "revision": 0,
  "generation_error": null
}
```

### 4.3 Mutation Contract

所有 PATCH、DELETE task、order、retry 和 regenerate 请求携带 `expected_revision`。成功后返回新的 plan revision。

```json
PATCH /plans/{plan_id}/tasks/{task_id}
{
  "expected_revision": 12,
  "title": "整理 Kubernetes 项目证据",
  "status": "in_progress",
  "due_date": "2026-08-10"
}
```

字段缺失代表不修改；显式 null 只允许清空 `due_date`。AI 任务编辑后仍保留 `source=ai` 和原 basis；若用户将 basis 不适用，可删除任务并新建 manual task。

### 4.4 Plan Detail Response

```json
{
  "id": "uuid",
  "title": "Example - Backend Engineer 求职计划",
  "status": "active",
  "progress": {"done": 3, "total": 18, "percent": 17},
  "revision": 12,
  "is_generation_stale": false,
  "jd": {"id":"uuid","title":"Backend Engineer","company":"Example"},
  "resume": {"id":"uuid","display_name":"resume.pdf"},
  "tasks": [],
  "generation_error": null,
  "updated_at": "2026-08-03T10:00:00Z"
}
```

`is_generation_stale=true` when `jd.updated_at > generated_at` or `profile.updated_at > generated_at` or generation preferences changed after generated_at。该标记只提示用户，不自动重生成。

### 4.5 List Contract

Query: `page`, `page_size<=100`, `q<=100`, optional `status`, `sort=updated_at`, `direction`。List item 包含 plan title、JD title/company、resume display name、progress、next due task、status、updated_at。next due task 使用单次聚合查询取得，不逐项查询。

### 4.6 Error Codes

| Code | Condition | Recovery |
|---:|---|---|
| 1001 | 参数或任务字段非法 | correct input |
| 1002 | plan/task/JD/resume 不存在 | return to list |
| 1003 | 状态不允许当前操作 | refresh state |
| 1006 | 同一 JD + Resume 已有未完成计划 | open existing plan |
| 1007 | expected_revision 冲突 | fetch latest and reconcile |
| 1008 | JD 非 ready 或 Candidate Profile 不存在 | complete upstream flow |
| 1009 | task 上限或排序集合不完整 | adjust request |
| 428 | LLM 未配置或未验证 | open settings |
| 5001 | LLM 调用失败 | retry |
| 5004 | Celery broker 派发失败 | retry |
| 5006 | LLM 计划结构或 basis 校验失败 | retry |

业务错误继续使用 `APIResponse.code`；FastAPI schema 错误使用 HTTP 422。前端 `apiRequest` 必须保留 response body 的 code/message，而不是只显示 transport status。

### 4.7 Breaking Changes

- RIP-008 只新增 API 与表。
- `GET /api/v1/resume` 是新列表接口，不改变现有 `/resume/{id}`。
- RIP-007 删除 JD 时会因新 FK 转为受保护行为。

## 5. Business Logic

### 5.1 Plan State Machine

```text
create -> generating
generating -> active | failed
failed -> generating (retry)
active -> completed (all tasks done)
completed -> active (new task or task reopened)
active/completed -> regenerating
regenerating -> active (success)
regenerating -> previous active/completed state (failure)
any state -> deleted
```

- Initial generation failed 时没有部分 AI tasks。
- Regeneration 期间现有 tasks 继续可读，但 mutation endpoints 返回 1003，避免并发编辑被替换。
- 计划 tasks 为空时状态为 active，不自动 completed。

### 5.2 Match Selection

1. 查询相同 jd/resume 的最新 JDMatchResult。
2. 若不存在，运行 JDMatchingService。
3. 若 `match.created_at` 早于 JD 或 Candidate Profile 的 `updated_at`，运行新 match。
4. match 与 generation input 在同一 worker run 中固定，生成中输入后续变化只产生 stale 标记。

### 5.3 Schedule Normalization

- Effective start = worker 当前 UTC 日期转换为应用时区日期。
- Effective target = 用户 target_date，否则 start + 28 days。
- LLM 输出 `due_offset_days`；服务端计算 `start + offset`。
- due date 超过 effective target 时 clamp 到 target。
- 同一 category 的任务按 due date、priority、LLM order 排序。
- weekly_hours 进入 prompt 作为任务粒度约束，不换算成精确工时承诺。

### 5.4 Progress and Completion

- `total` 为当前所有 task 行数；`done` 为 status=done 行数。
- `percent = round(done / total * 100)`；total=0 时为 0。
- 最后一项转 done 后 plan -> completed。
- completed 计划新增任务或 reopen task 后 plan -> active。
- 删除最后一个未完成任务后，若至少存在一个 task 且全部 done，plan -> completed。

### 5.5 Revision Control

每次 plan 或 task mutation 执行条件更新：

```text
UPDATE job_search_plans
SET revision = revision + 1, updated_at = now()
WHERE id = :id AND revision = :expected_revision
```

受影响行为 0 时返回 1007。任务写入和 revision 更新必须在同一事务，不能先写 task 后发现冲突。

### 5.6 Safe Regeneration

1. API 校验 revision/state/LLM/JD/Profile，保存 `previous_status`，设置 regenerating 和新 run id。
2. completed 计划若已有同 JD + Resume 的另一未完成计划，返回 1006，不进入 regenerating。
3. Worker 在事务外完成 match、Catalog、LLM 和 schema validation。
4. Final transaction lock plan row并验证 run id。
5. 保留所有 `source=manual` task。
6. 保留所有 `status=done` task，包括 AI done task。
7. 删除其余 `source=ai AND status!=done` tasks。
8. 插入新 AI tasks；保留项相对顺序不变，新项按生成顺序追加。
9. 更新 match/snapshot/model/generated_at，清错，status=active，revision+1。
10. 任一步失败：不修改 task 集合，恢复 previous status，记录 generation_error。

### 5.7 Delete Rules

- 删除计划前使 generation_run_id 失效；旧 worker 不能重建数据。
- 删除 plan 级联删除 tasks，不删除 JD、Resume 或 Match。
- done task 不允许单独删除；用户需要先 reopen，减少误删已完成记录。

## 6. Error Handling

### 6.1 Retry Strategy

- LLM generation time limit 180 秒，最多重试 2 次，间隔 30 秒。
- Match 计算失败与 LLM 失败分开记录日志，但对用户统一映射为可重试生成失败。
- 首次失败由 `/retry` 重新生成 run id，不创建新 plan。
- Regeneration 失败回到 previous status，原 tasks 保持不变。
- Broker 派发失败在 API 中立即落为 failed 或恢复 previous status。

### 6.2 Failure Persistence

- `generation_error` 只保存安全摘要，不保存 prompt、完整简历或 provider 响应。
- 结构化日志包含 `plan_id/run_id/step/model/error_type`。
- input_snapshot 是去敏业务快照；不得包含身份联系方式或 LLM 密钥。

### 6.3 Transaction Boundaries

- 外部 LLM 调用不持有数据库事务。
- 初次任务批量插入与 active 状态同一事务。
- Regeneration 替换集合必须单事务完成。
- 单任务 mutation 与 plan revision 同一事务。

## 7. Security

### 7.1 Authentication and Ownership

- `user_id` 可空，本期仍为匿名单用户域，不宣称多用户隔离。
- 当前 user context 可用后，plan/JD/resume 三者必须属于同一 user。
- 多人共享属于 TODO-PLAN-005，不在本期添加 ACL。

### 7.2 Prompt Injection and Data Minimization

- JD、Profile 和 supplemental background 均视为不可信内容。
- prompt 只允许从 Source Catalog 引用依据，未知 basis id 拒绝入库。
- Candidate Profile identity 中的姓名、电话、邮箱、地址不进入 prompt snapshot，除非未来需求明确授权。
- UI 将 description/basis 作为文本渲染，不执行 HTML。

### 7.3 Validation Limits

- title 200、supplemental 10000、task title 300、description 3000。
- 每个 plan 最多 200 tasks；批量排序必须精确包含当前全部 task IDs 且无重复。
- basis 最多 10 项，每项 excerpt 最多 500 字符。

## 8. Performance

### 8.1 Expected Load

- MVP 目标：单用户 1000 个计划、每计划最多 200 tasks。
- Create/regenerate API 只持久化并派发，正常 p95 < 500ms。
- Plan list/detail 数据库查询 p95 < 500ms，不包含生成轮询等待。

### 8.2 Query Strategy

- 列表使用聚合子查询一次计算 done/total 和 next due task，禁止 N+1。
- 详情使用 selectin load tasks 与轻量 JD/Resume 摘要，不加载完整 raw_text/Profile。
- Source Catalog 在 worker 单次加载 JD、Profile、Match 后于内存构建。
- progress 不落库，避免任务 mutation 时维护冗余计数。

### 8.3 Frontend Save and Polling

- generating/regenerating 每 2 秒轮询，60 秒后退避到 5 秒，终态或页面隐藏时停止。
- 状态和完成勾选立即保存；文本/日期/优先级编辑 debounce 500ms。
- 同一 task 的 mutation 串行发送；收到 1007 时停止队列、拉取最新 revision 并提示冲突。
- 保存失败保留本地 draft，不以服务端旧值覆盖。

## 9. Testing Strategy

### 9.1 Unit Tests

- Source Catalog 去敏、ID 稳定、basis resolution、未知 ID 拒绝。
- Match fresh/stale selection。
- 六分类、任务数量、字段长度、重复标题和 date clamp 校验。
- Progress/status transitions、revision conflict、task limit。
- Regeneration preservation matrix: manual/done/unfinished AI。
- LLM failure and stale run no-op。

### 9.2 Integration Tests

- Alembic upgrade/downgrade、FK RESTRICT、partial unique index。
- Create -> worker mock -> active；invalid upstream；duplicate plan；broker failure。
- Retry、regenerate success/failure atomicity。
- Task CRUD/order/revision conflict/completion transitions。
- Plan list pagination/search/status/progress/next due query count。
- Eligible resume list只返回 Candidate Profile 已存在的简历。
- RIP-007 JD delete referenced behavior。

### 9.3 Browser Acceptance

- 桌面与移动导航包含 JD 列表和计划列表，按钮与文字无重叠。
- 创建页支持从 JD 或 Resume 深链预选，并正确禁用缺失输入。
- generation loading 尺寸稳定，成功、失败和 retry 可见。
- 第二次及后续任务编辑、勾选、排序均可持续工作；刷新后持久化。
- 保存失败保留用户输入；revision conflict 不静默覆盖。
- Regenerate dialog 明确保留范围；成功保留 done/manual，失败保持原列表。

### 9.4 Acceptance Mapping

| PRD | Primary verification |
|---|---|
| US-001 / FR-1~3,8,9 | migration + persistence integration |
| US-002 / FR-4~6,22,23 | create validation + duplicate plan tests + browser |
| US-003 / FR-7~10,21 | generator, catalog, failure and schema tests |
| US-004 / FR-11~15 | task CRUD/revision/progress + repeated browser edits |
| US-005 / FR-16~19 | regeneration matrix and atomic failure tests |
| US-006 / FR-20 | list aggregate API + all UI states |
| US-007 / FR-2~5 | JD/Resume deep-link integration tests |

## 10. Implementation Plan

### 10.1 Phases

1. Plan/task models, migration, enums, schemas and design docs.
2. Eligible resume query, match freshness and Source Catalog builder.
3. LLM plan generator, prompt and strict validation.
4. Celery initial generation, create/status/retry APIs.
5. Task CRUD, revision control and atomic regeneration.
6. Frontend types/API/navigation/list/create flow.
7. Detail task editor, autosave, ordering, progress and regeneration UI.
8. Integration, browser acceptance and regression against RIP-007.

### 10.2 Issue Mapping

| Logical Issue | Scope | Priority | Depends On |
|---|---|---|---|
| RIP8-I01 | Plan/task schema, migration, enums and contracts | high | RIP7-I05 |
| RIP8-I02 | Eligible resume API, match freshness and Source Catalog | high | RIP8-I01 |
| RIP8-I03 | LLM plan generator, prompt and output validation | high | RIP8-I02 |
| RIP8-I04 | Celery create/status/retry pipeline | high | RIP8-I03 |
| RIP8-I05 | Task CRUD, revision, progress and completion state | high | RIP8-I01 |
| RIP8-I06 | Atomic regeneration and protected delete behavior | high | RIP8-I03, RIP8-I05 |
| RIP8-I07 | Frontend API/types/navigation/list/create UI | high | RIP8-I04 |
| RIP8-I08 | Detail editor, autosave/order/progress/regenerate UI | high | RIP8-I05, RIP8-I06, RIP8-I07 |
| RIP8-I09 | Integration, browser acceptance, design docs and RIP-007 regression | medium | RIP8-I08 |

### 10.3 Incremental Delivery

- Backend plan creation remains unlinked from navigation until initial generation integration passes.
- Plan list/create UI can ship before task editing only behind an internal route; public navigation waits for detail actions.
- TODO-PLAN-001 ~ 008 不生成本期 implementation Issues；保留在 PRD 的 Post-MVP 表，后续各自进入 PRD/SPEC 流程。

## 11. Open Questions and Risks

### 11.1 Resolved Product Questions

- 同一 JD + Resume：同一时间仅一份未完成计划；completed 后允许新建。
- MVP progress：按任务数量计算，不使用权重。
- 空白计划：本期禁止，保留 TODO-PLAN-008。

### 11.2 Technical Risks

| Risk | Impact | Mitigation |
|---|---|---|
| LLM 生成看似具体但依据不足 | 计划误导用户 | Source Catalog + basis ID 强校验 + 待补充标记 |
| Autosave 与排序并发覆盖 | 用户编辑丢失 | plan revision + per-task serialized queue |
| Regeneration 删除用户工作 | 信任与数据损失 | staging generation + atomic replace + preserve matrix |
| JD/Profile 更新导致旧计划 | 建议失真 | generated_at stale 标记；用户显式 regenerate |
| Plan feature依赖 RIP-007 migration | 实施顺序阻塞 | RIP8 migration和 API 明确依赖 RIP7-I05 |

### 11.3 Assumptions

- 应用时区使用 `Asia/Shanghai` 生成用户可见日期，数据库时间仍使用 UTC。
- 未指定 target_date 时使用 28 天 horizon，未指定 weekly_hours 时生成使用 8 小时。
- 当前 Candidate Profile 是计划背景的权威来源；supplemental background 只补充约束，不反写 Profile。
- Post-MVP TODO 不在本期创建 Issues，避免与 MVP 完成定义混杂。
