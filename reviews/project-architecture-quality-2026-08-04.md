# 项目整体架构质量评估

**审查时间**：2026-08-04 11:59:13 +08:00（Asia/Singapore）  
**评估范围**：`main` 分支当前工作树，基线提交 `89c87f6`；包含未提交的 Resume Builder、RIP-009 隐私相关改动。  
**评估方式**：对照 `README.md`、`current/`、`design/`、`specs/`，检查源码依赖、测试组织、异常与日志实现，并执行后端 lint/mypy/pytest 和前端 lint/build。

## 结论

整体评分为 **2.4/5**。项目已经具备可识别的 FastAPI + React/Vite 模块化单体形态，解析器工厂、LLM Gateway、Provider 抽象、前端 API client 和 feature 目录为后续扩展提供了基础；但实际依赖方向、错误契约、测试闭环和文档状态还没有稳定到适合多人持续扩展或生产化的程度。

当前最需要优先处理的不是继续增加功能，而是收敛边界和质量门禁：后端 `ruff` 有 14 个问题、`mypy` 有 45 个错误，测试结果为 231 个通过、4 个失败；失败集中在当前新增的隐私脱敏与 Builder 行为，说明实现、测试和规格仍未完全同步。

## 多维度评分表

评分口径：1 分 = 严重不足，3 分 = 可用但存在明显治理成本，5 分 = 稳定、清晰且可持续演进。

| 维度 | 评分 | 当前判断 | 主要证据 | 主要风险与建议 |
|---|---:|---|---|---|
| 架构清晰度 | 3/5 | 设计层面清楚：模块化单体、API/Application/Domain/Infrastructure、Celery 和 LLM Gateway 的职责都有文档；实现层面存在明显边界穿透。 | [backend-architecture.md](../design/backend-architecture.md#1-architecture-style) 已承认不是严格 Ports-and-Adapters；`backend/domain/resume/services.py:20-36`、`backend/domain/jd/services.py:15-26`、`backend/domain/job_search_plan/services.py:15-27` 直接依赖基础设施或应用层；多个 API 路由直接操作 ORM/MinIO/任务。 | 领域层难以独立演进和替换基础设施。先建立“API -> Application -> Domain/Ports -> Infrastructure”约束，逐个迁移高频路径，不建议一次性重写。 |
| 可测试性 | 3/5 | 后端有较完整的 unit/integration 分层和 LLM/解析器替身；但测试强依赖 PostgreSQL，领域服务直接绑定 SQLAlchemy/外部适配器，前端没有自动化测试。 | `backend/tests/` 扫描到 39 个测试文件、217 个测试函数；`backend/tests/conftest.py:16-23` 使用独立 PostgreSQL，`26-44` 数据库不可用时跳过；`frontend/package.json` 没有 test script，也没有前端 test/spec 文件。 | 单测容易被基础设施和模型变化牵连，前端回归主要依赖手工验证。补充纯领域测试、契约测试和关键页面浏览器测试，并在 CI 明确跳过/阻断策略。 |
| 可维护性 | 2/5 | 功能增多后，核心文件已经承担过多职责，变更影响面偏大。 | `frontend/src/pages/BuilderPage.tsx` 1821 行；`backend/infrastructure/db/models.py` 667 行；`backend/domain/resume_builder/services.py` 572 行；`backend/api/v1/resume_builder.py` 549 行；`backend/api/v1/resume.py` 513 行。 | 修改一个流程需要同时理解路由、ORM、脱敏、对象存储、LLM 和渲染。优先拆分 Builder、Resume Pipeline、ORM models 和 API serializer，按用例/聚合拆成小模块。 |
| 可扩展性 | 3/5 | 解析器工厂、`ResumeParser`、LLM Provider、Evaluator/Classifier 接口和 Celery 边界是可复用的扩展点。 | [parsers/__init__.py](../backend/infrastructure/parsers/__init__.py#L15-L36)、[providers/base.py](../backend/infrastructure/llm/providers/base.py#L16-L24)、[gateway.py](../backend/infrastructure/llm/gateway.py#L16-L36)。 | 扩展点下游仍被 ORM 和具体 SDK 反向耦合；前端类型手工维护，API 变更需要同步多个文件。保留现有抽象，增加 application-owned ports、OpenAPI/契约生成和架构依赖检查。 |
| 代码规范性 | 2/5 | 有 Ruff、mypy、TypeScript 和前端 Oxlint 配置，但当前工作树未达到门禁要求。 | `ruff check backend`：14 个错误；`mypy backend`：45 个错误；存在 `backend/api/v1/resume.py:319` 未定义的 `FileModel`；`backend/pyproject.toml:5` 声明支持 Python `>=3.11`，但 `backend/infrastructure/db/repositories.py:14` 使用 Python 3.12 的泛型类语法。前端 lint/build 通过，但 build 有约 1 MB 主 chunk 警告。 | 类型/格式问题会掩盖真实回归，并造成新人对支持版本的误判。先恢复 lint/type/test 全绿，再把它们作为合并门禁。 |
| 错误处理 | 2/5 | 部分业务已有错误码、重试、状态机和版本冲突处理；但 API 同时使用业务 `code`、HTTPException 和裸 `ValueError`，全局处理器覆盖面不足。 | `backend/main.py:40-58` 只注册 3 类全局异常；`backend/api/v1/plans.py:40-42` 将领域异常转成业务码；`backend/api/v1/interview.py:227-240`、`:271-275` 捕获宽泛异常；`backend/domain/resume/services.py:122-126` 将原始异常字符串写入 `parse_error`，状态接口会回传它。 | 客户端需要重复判断 HTTP 状态和业务码，异常可能泄露内部细节。统一 `AppError(code, http_status, public_message, retryable)`，由全局 handler 映射；禁止把原始异常直接作为用户可见错误。 |
| 日志质量 | 2/5 | 已有资源 ID、重试次数和异常堆栈等有用日志，LLM Agent/任务/工作流覆盖尚可；缺少统一格式、关联 ID、脱敏和集中配置。 | 后端约 49 处 logger 调用，但未发现 `basicConfig`/`dictConfig`、`request_id`/`trace_id` 或 OpenTelemetry 贯通；`backend/api/v1/interview.py:229-240`、`backend/tasks/interview_tasks.py:109-113` 有异常日志，`backend/application/plan_regeneration_service.py:79-93` 的 dispatch 异常则只做状态补偿。 | 线上难以按一次请求串联 API、Celery、LLM 和数据库；部分异常会静默降级。建立结构化日志 schema，统一注入 request/job/resource/trace ID，并在日志出口做隐私校验。 |
| 新人上手 | 2/5 | `design/` 和 `backend/README.md` 对当前模块说明较好，但项目入口存在多套状态和历史文档，真实工作入口不唯一。 | `README.md` 推荐 LiteSpec；`current/project-status.md:3` 标记 GoalSpec 且仍指向 issue #038；最新提交主题是 JD library/search plans/resume assistant；当前又有未提交 RIP-009。`docs/design.md` 明确是历史草稿，但旧内容仍描述 Next.js；`specs/roadmap.md` 仍以 AIP-001~008 为主，实际规格已使用 RIP-001~009。 | 新人可能按过期功能或错误模式加载上下文。保留历史文档但在入口集中声明唯一当前模式、当前 feature、当前路线图，并定期清理 `current/`。 |
| 代码复用 | 3/5 | 解析器、LLM Gateway、前端 API client 和 UI primitives 有复用价值；但公共仓储未被使用，错误/轮询/序列化逻辑仍在多个页面和路由重复。 | `backend/infrastructure/db/repositories.py:14-44` 只有定义，仓库中未发现调用；`frontend/src/api/client.ts:3-40` 提供统一请求错误；Builder 又在 `frontend/src/api/builder.ts:64-83` 自建请求器；多个页面重复 `response.code !== 0`、loading/error/retry 处理。 | 抽象分裂和重复逻辑会让修复无法一致落地。保留真正稳定的 client/adapter，统一 API error decoder、分页、轮询和状态机；无使用场景的 BaseRepository 应删除或落地到明确聚合。 |

## 验证结果

| 检查项 | 结果 | 说明 |
|---|---|---|
| 后端 Ruff | 未通过 | 14 个问题，包含 import 排序、未使用导入、超长行和未定义名称。 |
| 后端 mypy | 未通过 | 45 个错误，涉及可选依赖、测试替身类型、API 参数类型和当前 Builder/Privacy 改动。 |
| 后端 pytest | 未通过 | 231 passed、4 failed、5 warnings；失败为 `test_photo_rendering.py` 3 个、`test_resume_builder_services.py` 1 个。 |
| 前端 Oxlint | 通过 | `cd frontend && pnpm lint` 通过。 |
| 前端生产构建 | 通过但有警告 | `pnpm build` 通过，主 JS chunk 约 1,036 KB，超过 Vite 默认 500 KB 提示线。 |

## 优先级建议

| 优先级 | 建议 | 完成标准 |
|---|---|---|
| P0 | 修复当前质量门禁和隐私/Builder 测试契约 | Ruff、mypy、pytest 全绿；明确脱敏后 identity 字段的预期，补齐 `FileModel` 导入和测试替身类型。 |
| P1 | 统一异常与 API 错误契约 | 领域异常有稳定 code/status/public message；全局 handler 覆盖未知异常；不回传原始 exception 文本。 |
| P1 | 收紧分层依赖 | API 不直接访问 MinIO/ORM/任务；Domain 不导入 Application/Infrastructure；至少为 Resume、Builder、Plan 三条主链路建立 ports。 |
| P1 | 建立日志基线 | JSON/键值结构化日志、request/job/trace ID、统一事件名、隐私字段禁止输出，并为 Celery/LLM 调用补齐关联字段。 |
| P2 | 拆分超大模块并统一复用 | BuilderPage、Builder API、Resume services、ORM models 按用例/聚合拆分；共享 client、轮询和分页错误处理。 |
| P2 | 收敛文档入口 | 更新 `current/`、`specs/roadmap.md` 和 `docs/spec-modes/` 的当前状态，明确历史文档与唯一启动顺序。 |
| P2 | 补齐前端验证 | 为上传、隐私审核、Builder 保存/冲突、计划生成等关键路径加入浏览器或组件测试，并覆盖空、加载、成功、失败状态。 |

## 评估假设

- 本报告评估的是当前工作树，不代表干净基线提交；未提交变更造成的测试失败已单独标注。
- 评估重点是架构与工程质量，不包含认证、多租户、生产部署安全审计的完整结论；这些能力在当前设计文档中也被标记为后续工作。
- 行数和静态扫描已排除 `backend/.venv`、缓存、`node_modules` 和生成的 `frontend/dist`。
