# SPEC: RIP-007 JD 列表与智能识别

> Technical specification derived from: `tasks/prd-jd-library.md`
> Generated: 2026-08-03 | Target branch: `main` | Base commit: `ef809e6` (dirty worktree)
> Status: Approved

## 1. Summary

### 1.1 What This SPEC Covers

本 SPEC 定义 JD 资料库的后端持久化、三种来源导入、Celery 异步处理、LLM 结构化抽取、人工修正保护、重复检测、列表与详情 API，以及对应前端页面。实现扩展现有 JD 领域，不重写 RIP-003 的 JD Extractor 或 JD Matching。

### 1.2 PRD Reference

- Source: `tasks/prd-jd-library.md`
- User Stories: US-001 ~ US-007
- Functional Requirements: FR-1 ~ FR-20
- Downstream dependency: RIP-008 通过 `jd_id` 使用 ready JD

### 1.3 Design Decisions Summary

| Decision | Choice | Rationale |
|---|---|---|
| Feature location | 扩展现有 `domain/jd`、`api/v1/jd.py` 和 `job_descriptions` | 保持 JD 单一聚合，避免与 RIP-003 重复 |
| Async execution | Celery chain + Redis | 与简历解析流水线一致，API 可先落库再返回 |
| Source endpoints | 新增 `/jd/import/*`，保留现有 `POST /jd` | 新流程异步化，不破坏已有调用方和测试 |
| Web extraction | `httpx` 安全抓取 + `trafilatura` 正文抽取 | 避免把导航、脚本和整页 HTML 直接交给 LLM |
| HTML persistence | 仅保存 URL 和清洗正文 | MVP 不保存 HTML 快照，降低存储与敏感信息风险 |
| File storage | 复用现有 MinIO bucket，使用 `jd/` 前缀和 `FileModel` | 不新增基础设施服务或 bucket 配置 |
| Edit provenance | `field_sources` JSONB 按字段记录 `llm/manual` | 重新识别时可默认保护人工修正 |
| Stale worker protection | 每次处理生成 `processing_run_id` | 防止重试或重新识别后，旧任务覆盖新结果 |
| Duplicate handling | `duplicate_pending` 状态 + 用户确认 | 文件/URL 的哈希只能在异步取文后确定 |
| Ownership | `user_id` 可空，本期仍为匿名单用户 | 为未来隔离预留，不扩张到鉴权实现 |
| Pagination | 后端分页，默认 20、最大 100 | 避免资料库增长后一次加载全部记录 |

## 2. Architecture

### 2.1 System Context

```text
JD List / Detail UI
        |
        v
FastAPI /api/v1/jd
        |-- persist JobDescriptionModel + optional FileModel
        |-- dispatch Celery chain
        v
Celery Worker
        |-- text: validate/normalize
        |-- file: MinIO download -> existing parser factory
        |-- url: SafeWebFetcher -> trafilatura
        |-- duplicate check
        |-- JDExtractor -> LLM Gateway
        v
PostgreSQL job_descriptions
        |
        +--> existing JDMatchingService
        +--> RIP-008 PlanService
```

### 2.2 Component Design

| Component | Responsibility |
|---|---|
| `JDImportService` | 校验输入、创建记录、保存文件、生成 run id、派发任务 |
| `JDSourceExtractor` | 按 text/file/url 取得并规范化纯文本 |
| `SafeWebFetcher` | URL 校验、DNS/IP 安全检查、手动重定向、流式限长抓取 |
| `JDProcessingService` | 状态迁移、重复检测、LLM 结果合并、失败记录 |
| `jd_tasks` | 执行 source -> duplicate -> LLM -> finalize Celery chain |
| Existing `JDExtractor` | 将纯文本转换为 JD 结构化结果 |
| JD API | CRUD、分页、状态、重试、重新识别、重复确认 |
| JD frontend | 列表、创建、轮询、详情、编辑及下游入口 |

### 2.3 Module Interactions

#### Text import

1. API 校验文本长度与 LLM 门禁。
2. 创建 `processing/queued` JD，保存原文并生成 `processing_run_id`。
3. 派发任务；worker 规范化文本、计算哈希并检查重复。
4. 无重复时调用 JDExtractor；成功写入结构化字段并转为 `ready`。

#### File import

1. API 校验扩展名、MIME 和 10MB 上限，创建 JD。
2. 文件写入 MinIO `jd/{owner_key}/{jd_id}/{uuid}.{ext}`，新增 `FileModel(owner_type="job_description")`。
3. worker 下载文件，复用 PDF/DOCX/TXT/Markdown parser 取得正文，再进入重复检测与 LLM 抽取。

#### URL import

1. API 仅接受 HTTP/HTTPS URL 并创建 JD。
2. worker 在每次请求和重定向前解析域名，拒绝非全局可路由地址。
3. `httpx` 流式读取受限响应，`trafilatura` 提取正文，再进入重复检测与 LLM 抽取。

#### Manual edit and re-extract

1. PATCH 修改字段时，将对应 `field_sources[field]` 设置为 `manual`。
2. 重新识别生成新 run id。
3. 默认只覆盖来源非 manual 的字段；`overwrite_manual=true` 才覆盖人工字段。

### 2.4 File Structure

```text
backend/
├── api/v1/jd.py                                  [MODIFY: list/import/patch/delete/state actions]
├── api/v1/router.py                              [UNCHANGED route registration]
├── api/v1/schemas.py                             [MODIFY: JD response schemas]
├── application/jd_import_service.py              [NEW]
├── celery_app.py                                 [MODIFY: include jd_tasks]
├── domain/jd/
│   ├── enums.py                                  [NEW]
│   ├── schemas.py                                [MODIFY: import/edit/list/extraction schemas]
│   └── services.py                               [NEW: merge/provenance/state logic]
├── infrastructure/db/models.py                   [MODIFY]
├── infrastructure/extractors/jd_extractor.py     [MODIFY: expanded output only]
├── infrastructure/llm/prompts/jd_extraction.py   [MODIFY: expanded schema]
├── infrastructure/parsers/                       [REUSE]
│   └── html_parser.py                            [MODIFY: expose in-memory visible-text fallback]
├── infrastructure/storage/minio_client.py        [MODIFY: bounded download helper]
├── infrastructure/web/
│   ├── __init__.py                               [NEW]
│   └── safe_fetcher.py                           [NEW]
├── tasks/jd_tasks.py                             [NEW]
├── pyproject.toml                                [MODIFY: trafilatura]
└── tests/
    ├── unit/test_jd_import_service.py             [NEW]
    ├── unit/test_safe_web_fetcher.py              [NEW]
    ├── unit/test_jd_processing.py                 [NEW]
    └── integration/test_jd_library_api.py         [NEW]

frontend/src/
├── App.tsx                                       [MODIFY: /jobs routes]
├── api/jd.ts                                     [NEW]
├── components/Layout.tsx                         [MODIFY: JD navigation]
├── components/jd/
│   ├── JDImportDialog.tsx                        [NEW]
│   ├── JDEditor.tsx                              [NEW]
│   └── JDStatusBadge.tsx                         [NEW]
├── i18n/locales/en.ts                            [MODIFY]
├── i18n/locales/zh.ts                            [MODIFY]
├── pages/JDDetailPage.tsx                        [NEW]
├── pages/JDListPage.tsx                          [NEW]
└── types/jd.ts                                   [NEW]

infra/alembic/versions/<revision>_add_jd_library.py [NEW]
```

## 3. Data Model

### 3.1 `job_descriptions` Changes

| Column | Type | Null | Default | Purpose |
|---|---|---:|---|---|
| `user_id` | UUID FK users | yes | null | 未来用户隔离预留 |
| `source_type` | varchar(20) | no | `text` | `text/file/url` |
| `source_url` | varchar(2048) | yes | null | URL 来源 |
| `source_file_id` | UUID FK files | yes | null | 文件来源 |
| `location` | varchar(200) | yes | null | 工作地点 |
| `preferred_skills` | JSONB | no | `[]` | 加分技能及 evidence |
| `status` | varchar(30) | no | `ready` | `processing/duplicate_pending/ready/failed` |
| `processing_step` | varchar(30) | no | `done` | `queued/source_extract/duplicate_check/llm_extract/done` |
| `processing_error` | text | yes | null | 安全的用户可见错误摘要 |
| `processing_run_id` | UUID | yes | null | 当前有效 worker run |
| `duplicate_of_id` | UUID FK job_descriptions | yes | null | 疑似重复对象 |
| `content_hash` | char(64) | yes | null | 规范化正文 SHA-256 |
| `field_sources` | JSONB | no | `{}` | 字段级 `llm/manual` 来源 |
| `parser_version` | varchar(50) | yes | null | 来源正文解析器版本 |
| `updated_at` | timestamptz | no | now | 列表排序与匹配失效判断 |

现有 `title/company/raw_text/required_skills/responsibilities/seniority/extraction_source/structured/created_at` 保留。`raw_text` 在 file/url source_extract 完成前使用空字符串以满足现有非空约束；空字符串不得被视为可用正文。`structured` 只为兼容保留，新流程不再把核心字段重复写入该 JSONB。

### 3.2 Constraints and Indexes

- Check: `source_type IN ('text','file','url')`。
- Check: `status IN ('processing','duplicate_pending','ready','failed')`。
- Check: `processing_step` 只能取约定值。
- FK `source_file_id -> files.id ON DELETE SET NULL`。
- Self FK `duplicate_of_id -> job_descriptions.id ON DELETE SET NULL`。
- Index `(user_id, updated_at DESC)`、`(user_id, status)`、`(user_id, source_type)`。
- Index `(user_id, content_hash)`；匿名 MVP 下 `user_id IS NULL` 视为同一数据域。
- 搜索首版使用 `ILIKE`，不引入 pg_trgm。

### 3.3 Domain Schemas

```python
JDSourceType = Literal["text", "file", "url"]
JDStatus = Literal["processing", "duplicate_pending", "ready", "failed"]
JDProcessingStep = Literal[
    "queued", "source_extract", "duplicate_check", "llm_extract", "done"
]

class JDStructuredPatch(BaseModel):
    title: str | None
    company: str | None
    location: str | None
    seniority: Literal["junior", "mid", "senior", "expert"] | None
    responsibilities: list[str] | None
    required_skills: list[ExtractedSkill] | None
    preferred_skills: list[ExtractedSkill] | None
    expected_updated_at: datetime
```

PATCH 使用 `model_fields_set` 区分“未传字段”和“明确清空字段”。`expected_updated_at` 用于避免详情页多标签页静默覆盖。

### 3.4 Migration Plan

1. 实施时以工作区实际单一 Alembic head 为 `down_revision`；不得回接旧的 `e5f6...`。
2. 添加可空字段和带 server default 的状态字段。
3. 回填历史 JD：`source_type=text`、`status=ready`、`processing_step=done`、`field_sources` 根据现有 `extraction_source` 生成。
4. `updated_at` 回填 `created_at`。
5. 创建约束和索引。
6. 应用代码稳定后再移除迁移期 server defaults；本期可保留安全默认值。
7. Downgrade 只删除新增字段/索引，不删除历史 JD 主字段。

## 4. API Design

### 4.1 Endpoints

| Method | Path | Description | Request |
|---|---|---|---|
| GET | `/api/v1/jd` | 分页列表 | query filters |
| POST | `/api/v1/jd/import/text` | 异步导入文本 | JSON |
| POST | `/api/v1/jd/import/file` | 异步导入文件 | multipart |
| POST | `/api/v1/jd/import/url` | 异步导入公开网页 | JSON |
| GET | `/api/v1/jd/{jd_id}` | 详情及状态 | path |
| PATCH | `/api/v1/jd/{jd_id}` | 编辑结构化字段 | JSON |
| DELETE | `/api/v1/jd/{jd_id}` | 删除未被计划引用的 JD | path |
| POST | `/api/v1/jd/{jd_id}/retry` | 重试 failed JD | none |
| POST | `/api/v1/jd/{jd_id}/reextract` | 重新识别 ready JD | JSON |
| POST | `/api/v1/jd/{jd_id}/duplicate/confirm` | 确认保留并继续处理 | none |
| POST | `/api/v1/jd/{jd_id}/duplicate/cancel` | 删除未确认的重复记录 | none |
| POST | `/api/v1/jd` | 旧同步 JSON 创建 | existing contract |

所有新接口继续使用 `APIResponse {code,message,data}`。按现有 API guideline，业务错误保留 HTTP 200 并放入 `code`；Pydantic/文件协议错误使用 HTTP 422。前端必须同时处理 transport error 与非零业务 code。

### 4.2 Request Contracts

```json
POST /api/v1/jd/import/text
{
  "raw_text": "...",
  "title": null,
  "company": null,
  "allow_duplicate": false
}
```

- `raw_text`: trim 后 1 ~ 100000 字符。
- `title/company`: 各最多 200 字符，仅作为人工预填值，来源标记为 manual。

```json
POST /api/v1/jd/import/url
{
  "url": "https://example.com/jobs/123",
  "allow_duplicate": false
}
```

- URL 最大 2048 字符，只允许 HTTP/HTTPS，无凭证段。

`POST /import/file` 使用 `multipart/form-data`：字段 `file`，允许 `.pdf/.docx/.txt/.md`，最大 10MB；文件名与 MIME/扩展名必须通过双重校验。

```json
POST /api/v1/jd/{id}/reextract
{
  "overwrite_manual": false
}
```

### 4.3 Response Contracts

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "uuid",
    "status": "processing",
    "processing_step": "queued",
    "processing_error": null,
    "source_type": "url",
    "title": null,
    "company": null,
    "updated_at": "2026-08-03T10:00:00Z"
  }
}
```

List response:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

Query: `page>=1`, `1<=page_size<=100`, `q<=100`, optional `source_type`, optional `status`, `sort=updated_at`, `direction=desc|asc`。未识别完成的列表项不得伪造岗位或公司，前端显示来源文件名/域名作为 fallback。

### 4.4 Error Codes

| Code | Condition | Retryable |
|---:|---|---|
| 1001 | 参数、文件类型、大小或 URL 格式错误 | no |
| 1002 | JD 不存在 | no |
| 1003 | 当前状态不允许操作或 `expected_updated_at` 冲突 | after refresh |
| 1004 | 检测到疑似重复，状态为 `duplicate_pending` | user decision |
| 1005 | JD 被计划引用，不能删除 | no |
| 428 | LLM 未配置或未验证 | after config |
| 5001 | LLM 抽取失败 | yes |
| 5003 | 文件或网页正文提取失败 | yes |
| 5004 | Celery broker 派发失败 | yes |
| 5005 | URL 被 SSRF 安全策略拒绝 | no |

### 4.5 Breaking Changes

- 现有 `POST /api/v1/jd`、`GET /api/v1/jd/{id}` 和 `/jd/match` 保持兼容。
- `JobDescriptionData` 只新增可选字段。
- 静态路由 `/import/*` 必须在 `/{jd_id}` 之前注册，避免被 UUID path 捕获。

## 5. Business Logic

### 5.1 State Machine

```text
create -> processing/queued
processing/source_extract -> processing/duplicate_check
processing/duplicate_check -> duplicate_pending OR processing/llm_extract
duplicate_pending -> processing/llm_extract (confirm) OR deleted (cancel)
processing/llm_extract -> ready/done
any processing step -> failed/<failed step>
failed -> processing/<failed step> (retry)
ready -> processing/llm_extract (reextract)
```

只有携带当前 `processing_run_id` 的 worker 可以更新记录。旧 run 发现不匹配时必须无副作用退出。

### 5.2 Normalization and Duplicate Detection

1. Unicode NFKC 规范化。
2. 换行统一为 `\n`。
3. 连续空白折叠，trim 首尾。
4. 空正文或正文少于 30 个可见字符视为提取失败。
5. 超过 100000 字符时拒绝进入 LLM，不做静默截断。
6. 对规范化正文计算 SHA-256。
7. 同一用户域存在相同 hash 且不是当前记录时，转为 `duplicate_pending`。

### 5.3 LLM Result Merge

- Worker 必须通过 `get_active_verified_config(session)` 取得当前数据库配置，并使用 `LLMGateway.from_config`；没有配置时将记录置为 failed/code 428，不得退回环境变量默认模型。
- JDExtraction 扩展为 `title/company/location/seniority/responsibilities/required_skills/preferred_skills`。
- LLM 不确定的标量字段返回 null，列表返回空列表。
- 预填 title/company 视为 manual；首次识别不得覆盖。
- PATCH 涉及的字段写入 `field_sources[field]="manual"`。
- reextract 默认只覆盖来源为 llm 或空的字段。
- `overwrite_manual=true` 时覆盖全部结构化字段，并将来源改为 llm。
- `raw_text/source_url/source_file_id/content_hash` 不允许通过结构化 PATCH 修改。

### 5.4 Safe Web Fetch Rules

- 禁止 URL 中的 username/password、非 80/443 端口、非 HTTP/HTTPS scheme。
- 每一跳 DNS 解析后，所有 A/AAAA 地址都必须为 global address；拒绝 loopback、private、link-local、multicast、reserved、unspecified。
- `follow_redirects=False`，手动处理最多 3 跳，每跳重新验证 URL 和 DNS。
- `trust_env=False`，避免环境代理绕过目标校验。
- connect 5s、read 10s、总处理 20s。
- 流式读取最多 2MB；只接受 `text/html` 和 `text/plain`。
- `trafilatura` 无法取得正文时使用现有可见文本解析器作为单次 fallback；仍为空则失败。
- 不执行 JavaScript，不处理登录页、验证码或反爬绕过。

### 5.5 Retry Semantics

- source_extract 失败：retry 从 source_extract 开始。
- llm_extract 失败：raw_text 已存在时从 llm_extract 开始。
- LLM task 内部最多重试 2 次，间隔 30 秒，time limit 120 秒。
- source task 不自动重试；避免对外部 URL 或对象存储产生隐式重复访问。
- API retry 每次生成新 run id，清空用户可见错误，但保留上一段有效 raw_text。
- broker 派发失败时记录 failed，API 返回 code 5004。

### 5.6 Delete Rules

- `processing` 状态删除时先撤销当前 run：清空或替换 run id，使在途任务无权写回。
- `duplicate_pending` 可通过 cancel 删除。
- RIP-008 上线后，存在 plan FK 引用时返回 1005，不级联删除计划。
- 删除文件型 JD 时删除 `FileModel` 与 MinIO 对象；对象删除失败记录日志，数据库删除不回滚。

## 6. Error Handling

### 6.1 Failure Persistence

- 数据库只保存经过分类的安全错误摘要，不保存 API key、完整响应或堆栈。
- 完整异常进入结构化日志，字段含 `jd_id/run_id/step/error_type`。
- LLM 响应 schema 无效归类 5001；网络正文失败归类 5003；安全拒绝归类 5005。

### 6.2 Transaction Boundaries

- 创建 JD 与 FileModel、MinIO 上传采用补偿式流程：数据库失败时尝试删除对象。
- 每个 worker step 使用独立 session 和短事务。
- LLM 调用和网络抓取不持有数据库事务；先读快照，外部调用完成后再以 run id 条件更新。
- 结构化字段与 ready 状态必须在同一事务提交。

## 7. Security

### 7.1 Authentication and Ownership

- `user_id` 可空；本期没有登录依赖时所有记录属于同一匿名域。
- 后续引入 current user 后，所有列表、详情和重复检测查询必须按 user_id 限定。
- 本期不得声称已经实现多用户隔离。

### 7.2 Input and Prompt Safety

- 文件同时校验扩展名、MIME、大小，并使用既有解析器，不执行宏或嵌入脚本。
- 网页正文作为不可信数据，prompt 使用清晰边界并明确忽略正文中的指令。
- LLM 输出必须通过 Pydantic schema，字段长度和列表数量二次限制。
- 前端显示原文时按普通文本渲染，禁止 `dangerouslySetInnerHTML`。

### 7.3 Limits

- 文件 10MB；网页响应 2MB；清洗文本 100000 字符。
- responsibilities 最多 50 项；skills 每类最多 100 项；单项文本最多 500 字符。

## 8. Performance

### 8.1 Expected Load

- MVP 目标：单用户累计 10000 条 JD，列表页每次读取不超过 100 条。
- API 创建请求只执行校验、持久化和派发，正常不等待 LLM。
- 目标：不含 MinIO 上传的 JSON 创建 API p95 < 500ms；列表查询 p95 < 500ms。

### 8.2 Query Strategy

- 列表只选择 list item 字段，不加载 raw_text、structured 或关系集合。
- 详情按主键单次查询，文件元数据显式 join。
- `updated_at/status/source_type/content_hash` 使用组合索引支持主要查询。
- 不缓存 processing 状态，避免轮询读取陈旧数据。

### 8.3 Frontend Polling

- 详情或列表存在 processing 项时每 2 秒刷新状态。
- 连续 60 秒后退避到每 5 秒；终态、页面隐藏或组件卸载时停止。
- 单页面只维护一个轮询计时器，不为每个列表项单独建 timer。

## 9. Testing Strategy

### 9.1 Unit Tests

- `JDImportService`: 三种来源、文件约束、LLM 门禁、broker 失败补偿。
- `SafeWebFetcher`: scheme、凭证、端口、DNS 地址分类、每跳重定向、超时、响应上限、MIME。
- `JDProcessingService`: 状态迁移、run id 防旧写、hash、重复确认、字段来源合并。
- JDExtractor: 新字段正常、缺失、超长、非法 schema。
- 前端纯逻辑：query 序列化、状态映射、轮询停止条件。

### 9.2 Integration Tests

- Alembic upgrade/downgrade 与历史 JD 回填。
- 三个 import endpoint -> Celery task mock -> ready/failed/duplicate_pending。
- PATCH optimistic conflict、retry、reextract、delete referenced。
- 现有 POST `/jd` 和 `/jd/match` 回归。
- MinIO 文件上传/下载/删除集成。

### 9.3 Browser Acceptance

- 桌面与移动视口验证顶部导航无重叠。
- 验证三种创建模式、提交禁用态、processing 轮询、失败重试、重复确认。
- 验证编辑保存、刷新持久化、取消无写入、保存失败保留草稿。
- 验证 ready JD 的匹配和计划入口；RIP-008 未交付前计划入口不得形成死链。

### 9.4 Acceptance Mapping

| PRD | Primary verification |
|---|---|
| US-001 / FR-1,7,8 | migration + state integration tests |
| US-002 / FR-2~6,9~12 | import service, fetcher, parser, extractor tests |
| US-003 / FR-15 | list API tests + browser states |
| US-004 / FR-16,17 | import UI + duplicate browser flow |
| US-005 / FR-13,14 | PATCH/provenance/conflict tests + browser persistence |
| US-006 / FR-1,20 | retry/reextract/delete integration and browser tests |
| US-007 / FR-18,19 | downstream route integration tests |

## 10. Implementation Plan

### 10.1 Phases

1. Data model, migration, enums and schemas.
2. Source extraction primitives: MinIO download, file parser adapter, SafeWebFetcher.
3. Processing service and Celery chain with stale-run protection.
4. Import, list, edit, retry, reextract, duplicate and delete APIs.
5. Frontend types/API, navigation, list/import UI.
6. Detail editor, polling, recovery and downstream entry points.
7. Integration, regression, security and browser acceptance.

### 10.2 Issue Mapping

| Logical Issue | Scope | Priority | Depends On |
|---|---|---|---|
| RIP7-I01 | JD library schema, migration, enums and contracts | high | none |
| RIP7-I02 | Text/file import service, MinIO and parser reuse | high | RIP7-I01 |
| RIP7-I03 | Safe public URL fetch and body-text extraction | high | RIP7-I01 |
| RIP7-I04 | Celery processing pipeline, run id and duplicate state | high | RIP7-I02, RIP7-I03 |
| RIP7-I05 | JD list/detail/edit/delete/retry/reextract APIs | high | RIP7-I04 |
| RIP7-I06 | Frontend API/types/navigation/list/import UI | high | RIP7-I05 |
| RIP7-I07 | JD detail editor, polling, duplicate and downstream UI | high | RIP7-I05, RIP7-I06 |
| RIP7-I08 | Integration, security regression and browser acceptance | medium | RIP7-I07 |

### 10.3 Incremental Delivery

- Backend endpoints can ship before navigation exposure; old POST `/jd` stays active.
- Frontend routes are added only when list/detail APIs pass integration tests.
- RIP-008 plan link is exposed only when `/plans/new` exists; before that it remains absent, not disabled.

## 11. Open Questions and Risks

### 11.1 Resolved Product Questions

- File limit: 10MB, aligned with resume upload.
- Web snapshot: not stored in MVP.
- Duplicate scope: anonymous single-user domain now, per-user after auth.

### 11.2 Technical Risks

| Risk | Impact | Mitigation |
|---|---|---|
| JS-rendered job pages yield little text | URL import fails for some sites | 明确只支持公开静态正文；保留粘贴文本 fallback |
| DNS rebinding between validation and connection | SSRF residual risk | 每跳立即解析、禁用 env proxy；生产环境再加 outbound egress policy |
| Celery stale task overwrites reextract | 人工修改或新结果丢失 | processing_run_id 条件更新 |
| Expanded JD schema changes LLM quality | 抽取失败率上升 | schema tests、一次内部格式重试、evidence 校验 |
| Dirty migration chain changes before implementation | down_revision 冲突 | 创建迁移时读取实际单一 head，不硬编码当前草稿 head |

### 11.3 Assumptions

- 当前部署继续运行 Postgres、Redis、MinIO 和 Celery worker。
- 匿名单用户 MVP 不提供真实数据隔离，`user_id` 只是前向兼容字段。
- `trafilatura` 的实际版本由实现时 `uv lock` 固定，并纳入 parser regression tests。
- RIP-008 在删除保护和计划入口上依赖本 SPEC 的稳定 `jd_id` 合约。
