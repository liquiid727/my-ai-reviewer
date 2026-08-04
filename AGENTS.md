# AGENTS.md - Agent Interview Platform

本文件是仓库级 Agent 执行规范。它把需求、规格、实现、测试、评审和交付串成一条可追溯链路。任何代码、文档或测试任务都必须先读取本文件，再按任务范围加载项目上下文。

## 1. 规则优先级

发生冲突时按以下优先级处理：

1. 用户在当前任务中的明确要求。
2. 本文件中的仓库级规则。
3. `current/` 中带日期的当前交付状态。
4. `design/` 中的现状架构和稳定约束。
5. 当前功能的 `spec.md`、`tasks.md`、测试计划和验收标准。
6. `README.md`、`specs/roadmap.md` 及其他历史说明。
7. `CLAUDE.md`、`.agents/` 中的旧版或角色说明，仅作为补充；若与上述内容冲突，以较新的项目状态和 as-built 设计为准。

不要因为文档过时就静默猜测。记录假设，必要时把冲突写入 `current/blockers.md` 或当前功能的交付记录。

## 2. 任务开始前的上下文加载

按照以下顺序加载最小必要上下文，不要无目的地读取整个仓库：

1. `README.md`：项目目标、技术栈和入口。
2. `docs/spec-modes/README.md` 以及当前模式文件：`LiteSpec`、`GoalSpec` 或 `EnterpriseSpec`。
3. `current/README.md` 和与任务相关的 `current/` 文件：
   - `project-status.md`：当前模式、阶段和健康状态；
   - `active-feature.md`：正在交付的功能；
   - `active-tasks.md`：当前任务和下一步；
   - `active-context.md`、`blockers.md`、`handoff.md`、`sprint-status.md`：按需读取。
4. 读取 `spec-draft/README.md`；存在与任务相关的人类草稿时继续读取对应草稿。
5. 读取 `design/README.md`，再按影响范围读取 `design/`：
   - 所有代码任务至少读取 `design/coding-guidelines.md`；
   - API 任务读取 `api-guidelines.md`；
   - 数据库或迁移任务读取 `database.md`；
   - 后端、前端、部署或隐私任务读取对应架构文档。
6. `specs/roadmap.md` 和 `specs/issues/README.md`：确认依赖、发布顺序和 issue 状态。
7. 当前功能目录 `specs/<SPEC-ID>-<slug>/`：至少读取 `spec.md` 和 `tasks.md`；存在时同时读取 `tests.md`、`review.md`、`changelog.md`。
8. 读取 `rules/`、`specs/_rules/` 和 `ai/agents/` 中的仓库规则、Spec 规则及角色责任；再加载与任务角色匹配的 `.agents/*.skill.md` 或 `skills/` 下的项目技能。
9. 相关实现、迁移、测试、评审和历史交付证据：`backend/`、`frontend/`、`infra/`、`implementation/`、`reviews/`、`tests/`。

当前模式以 `current/project-status.md` 为准。若该文件标记为 `GoalSpec`，使用下面的六步交付循环；不要根据旧的 `CLAUDE.md` 或 `.agents/project-context.md` 推断当前仍处于早期 Phase 1。

## 3. 事实来源和产物归属

| 内容 | 规范来源 | 交付产物 |
|---|---|---|
| 项目目标和入口 | `README.md` | — |
| 当前模式和工作状态 | `docs/spec-modes/`、`current/` | `current/` 更新记录 |
| 稳定系统边界 | `design/` | 对应设计文档 |
| 史诗、依赖和发布顺序 | `specs/roadmap.md`、`specs/issues/README.md` | roadmap / issue 状态 |
| 功能行为和验收 | `specs/<SPEC-ID>-<slug>/spec.md` | 实现、测试、评审 |
| 实现交接和变更说明 | `implementation/` | implementation note |
| 单测和集成测试 | `backend/tests/` | 测试代码与运行结果 |
| 场景、API 计划和标准化结果 | `tests/` | `plans/`、`bruno/`、`results/` |
| 评审证据 | `reviews/` 及功能目录内的 `review.md` | review report |
| 仓库规则和角色职责 | `rules/`、`specs/_rules/`、`ai/agents/` | 规则或角色说明 |

`specs/` 使用现有的 `AIP-*`、`RIP-*` 等 Spec ID。新增功能必须沿用 `specs/roadmap.md` 和 issue 索引中的命名与依赖，不要自行引入另一套 ID 规则。

## 4. 任务分流和范围控制

开始修改前：

1. 运行 `git status --short`，确认用户已有改动和未跟踪文件。
2. 找到目标 Spec/issue、验收条件、受影响的模块和外部契约。
3. 判断任务属于后端、前端、数据库、隐私、文档、测试还是跨层变更。
4. 对模糊要求记录假设；如果会改变数据模型、API 契约、隐私策略或发布范围，先停下来请求确认或更新 spec。

小修复可以直接关联现有 issue；新功能按 `spec-draft -> design（必要时） -> spec -> issue -> implementation -> test -> review` 推进。一个 issue 应保持为可由单个 `/goal` 完成的、小而完整的端到端切片，避免顺手重构不相关模块。

## 5. 当前架构和依赖边界

这是一个 React/Vite 前端加 FastAPI/Celery 后端的模块化单体，不是微服务部署：

```text
Browser
  -> frontend/ React + TypeScript + Vite
  -> /api/v1
  -> backend/api/v1
  -> application services
  -> domain rules + infrastructure adapters
  -> PostgreSQL / Redis / MinIO / LLM gateway
                         ^
                  Celery worker
```

主要目录职责：

- `backend/api/`：HTTP 路由、请求解析和响应序列化；不得直接编排基础设施。
- `backend/application/`：用例编排和事务边界，调用 domain 与 infrastructure。
- `backend/domain/`：实体、值对象、枚举、领域服务和业务 schema；不得依赖 application 或 infrastructure。
- `backend/infrastructure/`：数据库、缓存、对象存储、解析器、渲染器、隐私处理和外部 LLM 适配器。
- `backend/workflow/`、`backend/agents/`：LangGraph 图、节点和 LLM-facing 能力；遵守应用层和领域层边界。
- `backend/tasks/`：Celery 入口和异步管线；使用资源 ID、run ID 或 revision 保证重试和过期 worker 不会覆盖新状态。
- `frontend/src/pages/`：路由级页面和工作流编排。
- `frontend/src/api/`：类型化 API 请求边界。
- `frontend/src/stores/`：跨页面 Zustand 状态；页面局部状态留在页面或组件。
- `frontend/src/components/`、`frontend/src/components/ui/`：可复用功能组件和 UI 原语。
- `infra/alembic/`：唯一的数据库迁移入口；schema 变更必须有迁移。

当前基础设施边界：PostgreSQL 是业务状态源，Redis 是队列/缓存，MinIO 保存上传文件和导出物。`Qdrant`、RAG、Memory、Multimodal、Sandbox 等目录可能只是扩展点；没有对应 spec、实现和测试时，不得把它们当作已启用的运行时服务。

## 6. 实现规则

### 后端

- Python 3.12 是当前开发目标；项目元数据最低声明为 Python 3.11，修改代码时遵守 `backend/pyproject.toml` 的配置。
- I/O 默认使用 `async/await`。不要在 FastAPI 路由、异步 service 或 worker 中引入未隔离的阻塞操作。
- 使用 Pydantic v2 做请求校验和 LLM 结构化输出；所有公开函数签名补齐类型注解。
- 使用 SQLAlchemy 2.x 的 `select()` 风格和 async session；禁止用 `session.query()` 旧式 API。
- API 只调用 application；domain 不调用数据库、LLM、对象存储或 application；provider-specific 逻辑集中在 infrastructure 的 LLM gateway/adapter。
- 所有 API 变更同时检查 `/api/v1` 路由、Pydantic schema、前端类型和相关 spec。除二进制导出外，遵循统一 `APIResponse` envelope。
- LLM 调用必须有明确的超时、异常处理和结构化输出约束。不要在日志、错误响应、prompt 或测试快照中写入 API key、原始简历或其他敏感信息。
- Celery 任务应可重试、可观测、幂等；用状态、run ID、revision 或显式锁保护较新的用户修改。
- 数据库、持久化字段或保留策略有变化时，补充 Alembic migration、`design/database.md` 和必要的回滚/兼容说明。

### 前端

- 使用 React 19、TypeScript、Vite、React Router、Zustand 和现有 UI 原语；不要根据旧文档引入 Next.js 结构。
- API 请求通过 `frontend/src/api/` 和现有 client 封装；同步更新 `frontend/src/types/`。不要在页面中散落重复的 fetch、响应解析或错误协议。
- 用户文案走 `frontend/src/i18n/`，保持中英文资源一致；不要把后端原始错误对象直接展示给用户。
- 每个数据页面和异步操作明确覆盖 loading、empty、success、failure、mutation pending，以及适用时的 conflict/expired 状态。轮询必须在终态、超时或页面失去所有权后停止。
- 保持现有响应式布局、Neobrutalism 视觉约定和 Lucide/Radix 组件体系。操作按钮使用合适的图标或现有组件，图标按钮提供可访问名称/tooltip。
- 二进制 PDF 导出、Builder proposal 和其他特殊契约应留在对应 feature module，不要污染通用 JSON client。

### 隐私和安全

- Resume Privacy 流程是跨模块约束：上传文件进入加密、短期 quarantine；本地 redaction 生成 placeholder、manifest 和 masked text；LLM 只能接收 masked content。
- `PrivacyGuard` 必须 fail closed。任何直接标识符泄露风险都应阻止调用，而不是降级为发送原文。
- quarantine 有 TTL 和明确删除路径；过期数据不能被后续审批。导出或恢复真实值只能使用 manifest 声明的精确 token，不能做任意全局替换。
- 浏览器状态、日志、测试 fixture、截图和评审证据不得包含真实个人信息。测试使用合成数据或已脱敏样例。
- API 当前是本地单用户开发表面，尚未具备完整认证、授权、租户隔离和生产级对象访问控制；不要把现有实现描述成 SaaS 级安全能力。

## 7. GoalSpec 交付循环

当 `current/project-status.md` 为 `GoalSpec` 时，标准链路为：

```text
/prd -> /prd-to-spec（可选） -> /to-issues -> /goal -> /review-it -> /ship-it
```

| 阶段 | 主要输入 | 必须留下的结果 |
|---|---|---|
| `/prd` | 产品意图 | `spec-draft/` 草稿 |
| `/prd-to-spec` | 已确认草稿 | 稳定设计更新或设计决策 |
| `/to-issues` | spec / design | issue 索引、任务拆分和依赖 |
| `/goal` | 一个小 issue | 代码、实现说明、实现耦合测试 |
| `/review-it` | diff、spec、测试结果 | `reviews/` 或功能 review 记录 |
| `/ship-it` | 通过的 review 和检查 | commit/PR/合并/关闭 issue、changelog |

`/prd-to-spec` 和 `/to-issues` 对单一明确的小改动可以省略，但验收标准和追踪关系不能省略。只有用户明确要求或已经授权交付时，才执行 commit、push、PR、merge 或关闭 issue；实现完成不等于自动发布。

状态更新规则：

- 开始或完成当前 issue 时同步更新相关 `specs/.../tasks.md`、`current/active-tasks.md` 和必要的 `current/project-status.md`。
- 发现无法在当前任务解决的依赖、环境或决策问题，写入 `current/blockers.md`，记录影响和下一步。
- 变更行为、架构边界、数据契约、保留策略或运行时依赖时，更新对应 spec/design，而不是只修改代码。
- 保留人类维护的原始草稿和历史记录；生成文件必须能追溯到 spec、rule、test plan 或脚本来源。

## 8. 测试和证据

先定义与验收条件对应的测试，再实现代码。风险较高或跨模块的改动要同时覆盖正常、空、加载、失败、重试、并发/过期和隐私边界。

测试位置：

- `backend/tests/unit/`：领域规则、parser、privacy、LLM adapter、renderer 和 service 单测。
- `backend/tests/integration/`：API、数据库和跨模块流程。
- `backend/tests/e2e/`：预留的后端完整流程。
- `tests/plans/`：由 spec 派生的 test plan。
- `tests/bruno/`：API 请求集合和断言。
- `tests/results/`：标准化场景/API 结果，必须带 `spec_id`、`run_id`、状态和证据引用。
- `reviews/`：评审证据；旧记录可能是扁平文件，新记录优先按 Spec ID 归档。

仓库当前可用命令：

```bash
# 初始化、依赖和本地基础设施
make setup
make install
make infra
make db-migrate

# 后端/前端质量检查
make lint
make test
PYTHONPATH=. uv run --project backend mypy backend
cd frontend && pnpm build

# 定向检查
PYTHONPATH=. uv run --project backend pytest backend/tests/unit/test_<name>.py -q
PYTHONPATH=. uv run --project backend pytest backend/tests/integration -q
PYTHONPATH=. uv run --project backend ruff check backend
cd frontend && pnpm lint

# 本地运行
make dev       # 基础设施 + 后端热重载 + worker + 前端 HMR
make backend   # 后端热重载
make backend-worker
make frontend   # 前端 HMR，默认 :5173
```

`make test` 当前运行 `backend/` 下的 pytest；集成测试通常需要 `make infra` 和正确的 `.env`。不要声称未运行的检查通过。若全库检查被已有错误、缺少服务或可选依赖阻塞，记录准确命令、失败原因、受影响范围和是否为本次变更引入；不要通过删除测试、放宽门槛或隐藏输出来“修复”结果。仓库没有 `make ci` 时不要假设该命令存在。

涉及页面、轮询、导出或浏览器交互的改动，除静态检查外进行实际浏览器验证，并记录关键路径和截图/结果位置。涉及数据库时验证迁移；涉及 API 时验证成功、业务错误、校验错误和资源不存在分支。

## 9. 完成检查清单

- [ ] 目标 spec/issue、范围和假设已确认。
- [ ] 实现遵守分层、类型、异步、API、数据和隐私边界。
- [ ] 所有受影响的 DB/API/前端类型/设计文档已同步。
- [ ] 用户流程覆盖 empty、loading、success、failure 和适用的 retry/conflict/expired 状态。
- [ ] 新增或修改的单测/集成测试已运行；失败和环境阻塞已留下证据。
- [ ] 测试计划、标准化结果、review 或 implementation note 按当前模式归档。
- [ ] `git diff --check`、相关 lint/build/test 已执行。
- [ ] 变更没有引入密钥、真实 PII、未追踪的生成产物或无关重构。
- [ ] 最终再次检查 `git status --short` 和 diff，确认没有覆盖用户已有改动。

## 10. Git、文件和破坏性操作

- 先读 `git status` 和目标文件，再编辑。工作树中的既有修改属于用户；不要使用 `git reset --hard`、`git checkout --` 或大范围删除来清理它们。
- 手工编辑使用 `apply_patch`；不要用 shell 重定向或脚本覆盖人类维护文件。
- 不要提交 `.env`、密钥、证书、真实上传文件、数据库数据、缓存或 `frontend/dist/` 等生成物。
- 删除、迁移或批量改写前先确认精确目标和可恢复性；目标不明确时停止并请求确认。
- 只修改完成当前任务所需的文件。无关改动即使看起来可以顺手优化，也保留给后续任务。

## 11. 交付说明

最终回复应简要说明：改了什么、涉及哪些文件、运行了哪些验证、哪些验证因环境或既有问题未完成，以及仍需用户决定的事项。不要把未执行的命令写成已通过，也不要遗漏隐私、迁移或发布方面的残余风险。
