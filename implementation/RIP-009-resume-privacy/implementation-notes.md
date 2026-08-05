# RIP-009 Celery 异步运行时修复

## Meta

- Spec ID: `RIP-009-resume-privacy`
- Status: implemented locally; review and worker restart pending
- Date: 2026-08-05
- Scope: Celery prefork worker、SQLAlchemy async engine、asyncpg connection lifecycle

## 问题与证据

日志中的主故障不是 `/api/state` 的 `404`。该路径没有当前后端路由，属于前端探测路径与 API 契约不一致；它没有造成简历处理任务失败。

简历任务失败的直接证据是：

- `asyncpg` 在释放连接时报告 `Future ... attached to a different loop`；
- 随后出现 `got result for unknown protocol state 3`，说明同一连接的协议状态已经被跨 loop 使用破坏；
- `resume_watchdog` 从共享 SQLAlchemy async engine 取连接时再次报告跨 loop；
- `text_extract` 被标记为 `RESUME_PROCESSING_FAILED`，后续链式任务收到并传播了 `failed` 状态。

原实现中，`resume_tasks`、`resume_watchdog`、JD、plan 和 interview task 各自创建或使用不同的 asyncio 入口，而 `backend.infrastructure.db.database` 暴露的是一个全局 SQLAlchemy async engine。连接池中的 asyncpg 连接绑定创建它的 event loop，因此同一 prefork 子进程内先后运行不同任务时，连接可能被 loop A 创建、被 loop B 借用或关闭。

## 采用的方案

本次采用“单 worker 子进程一个 async runner/event loop”作为主修复，并同时处理 prefork 的连接池继承边界：

1. `backend.tasks.async_runtime.run_async()` 按当前进程 PID 持有唯一 event loop。所有同步 Celery task 入口都通过它运行 coroutine。
2. `worker_process_init` 中调用 `async_engine.sync_engine.dispose(close=False)`。这会在 fork 子进程中丢弃父进程的连接池状态，但不关闭父进程可能持有的文件描述符。
3. `worker_process_shutdown` 在同一个 loop 上 await `async_engine.dispose()`，关闭 async generators，再关闭 loop。
4. `run_async()` 拒绝在已经运行的 loop 上重入，避免把同步 Celery 入口嵌套到同一 async 调用中。
5. 生产 worker 继续使用连接池，不额外切换到 `NullPool`。单 loop + fork 后重建 pool 已经建立了正确的连接所有权；测试中需要隔离 loop 的临时 engine 仍可按测试需要使用 `NullPool`。

这条约束适用于当前 Celery 默认 prefork worker。未来如果引入 threads、eventlet、gevent 或其他执行池，必须为其单独设计 engine/loop 生命周期，不能直接复用当前 task 入口。

## 修改范围

| 文件 | 作用 |
| --- | --- |
| `backend/tasks/async_runtime.py` | 统一 runner、PID 所有权、fork 初始化和 graceful shutdown |
| `backend/celery_app.py` | 注册 `worker_process_init` / `worker_process_shutdown` 生命周期钩子 |
| `backend/tasks/resume_tasks.py` | 移除模块级 loop，统一通过 runner 执行 |
| `backend/tasks/resume_watchdog.py` | 移除模块级 loop，统一通过 runner 执行 |
| `backend/tasks/jd_tasks.py` | 移除模块级 loop，统一通过 runner 执行 |
| `backend/tasks/plan_tasks.py` | 移除 `asyncio.run()`，统一通过 runner 执行 |
| `backend/tasks/interview_tasks.py` | 移除 `asyncio.run()`，统一通过 runner 执行 |
| `backend/tests/unit/test_celery_async_runtime.py` | 验证所有 task module 使用同一个 loop，并验证 fork pool reset |
| `backend/tests/integration/test_celery_async_runtime.py` | 同一 task process 顺序执行 watchdog -> resume task，并完成真实 PostgreSQL `SELECT 1` round-trip |
| `backend/tests/unit/test_resume_task_runtime.py` | 将既有 resume runner 测试迁移到共享 runner |

## 验证方式

先以失败测试确认旧行为：顺序执行 watchdog 和 resume task 时，测试复现了 `Future attached to a different loop`，随后出现连接仍在进行中的 asyncpg/SQLAlchemy 错误。

修复后的结果：

| Check | Result |
| --- | --- |
| Celery runtime + resume/JD/plan task unit tests | `13 passed` |
| watchdog -> resume real PostgreSQL integration test | `1 passed` |
| All backend integration tests | `41 passed` |
| All backend unit tests | `281 passed, 2 failed`；失败位于既有 Resume Builder fake model 字段，不涉及本次改动 |
| Targeted Ruff and format checks | pass |
| Architecture check | pass，`new=0`，33 条既有违规已豁免 |
| Targeted mypy with `backend/pyproject.toml` | pass，7 source files |
| Repository mypy | fail，16 个既有/环境相关错误；主要为缺失可选 imaging 依赖、Celery/fitz 存根、配置字段和旧测试类型 |

定向命令：

```bash
PYTHONPATH=. uv run --project backend pytest backend/tests/unit/test_celery_async_runtime.py -q
PYTHONPATH=. uv run --project backend pytest backend/tests/integration/test_celery_async_runtime.py -q
PYTHONPATH=. uv run --project backend pytest backend/tests/unit/test_resume_task_runtime.py -q
PYTHONPATH=. uv run --project backend ruff check backend/tasks backend/celery_app.py backend/tests/unit/test_celery_async_runtime.py backend/tests/integration/test_celery_async_runtime.py
PYTHONPATH=. uv run --project backend python scripts/quality/arch_check.py
```

全量验证命令：

```bash
PYTHONPATH=. uv run --project backend pytest backend/tests/unit -q
PYTHONPATH=. uv run --project backend pytest backend/tests/integration -q
PYTHONPATH=. uv run --project backend mypy backend
```

集成测试必须连接配置的测试 PostgreSQL，而不是只 mock session。测试先调用 `resume_watchdog.reconcile_resume_runs_task.run()`，再调用 `resume_tasks.text_extract_task.run()`；两个 task 共用一个真实 pool，并各自执行数据库 round-trip。

## 执行与上线步骤

1. 部署代码后停止旧 Celery worker。旧进程不会自动获得新的 signal hook，也可能继续持有旧 loop/pool。
2. 重新启动 worker 和 beat：

   ```bash
   make backend-worker
   make beat
   ```

3. 使用合成简历执行一次上传/处理流程，并观察 watchdog 后续周期。日志中不应再出现 `different loop`、`unknown protocol state` 或 `Exception terminating connection`。
4. 确认 `/api/v1/resume/{id}/status` 最终返回业务终态；`/api/state` 的 `404` 仍应通过前端请求路径修复单独处理，不要把它当作数据库故障。

本修复没有数据库 schema 变更，不需要新增 Alembic migration。回滚时恢复代码并完整重启 worker；不需要数据库回滚。

## 残余风险

- 仓库声明 Python 3.12 为 CI 目标，而当前本机日志来自 Python 3.13.3；发布前仍应在项目目标 Python 版本上复跑验证。
- 全库 lint/type/test 可能包含与本修复无关的历史失败。交付时必须把本次定向结果与全库基线失败分开记录。
- 当前 API 是本地单用户开发表面；本修复只处理 worker async resource ownership，不改变认证、授权或生产部署安全边界。
