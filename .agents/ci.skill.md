# CI Skill

适用于所有 CI 检查任务：代码质量、类型检查、测试运行、架构合规。

---

## 触发时机

| 场景 | 操作 |
|---|---|
| Feature 开发完成，准备提交 PR | 执行完整 CI 检查 |
| 修复 Bug 后 | 执行快速检查（lint + 单元测试） |
| Review 通过，准备合并 | 确认 CI 全绿 |

---

## 检查流程

### Step 1 — 静态分析（Lint + Format）

```bash
# 格式检查 + 修复
ruff check app/ --fix
ruff format app/

# 检查不通过则阻断，不允许 bypass
```

通过标准：`ruff check` 零报错，`ruff format --check` 无差异。

---

### Step 2 — 类型检查

```bash
mypy app/ --ignore-missing-imports --strict
```

通过标准：零 `error`，`warning` 可接受但需记录。

关键规则（对照 `design/coding-guidelines.md`）：
- 所有公开函数必须有完整类型注解
- Pydantic v2 模型字段必须有类型
- `async def` 返回值必须标注

---

### Step 3 — 架构合规检查

检查 DDD 分层是否有跨层调用：

```bash
# 禁止 api/ 直接 import infrastructure/
grep -rn "from app.infrastructure" app/api/ && echo "VIOLATION: api imports infrastructure" || echo "OK"

# 禁止 domain/ import application/ 或 infrastructure/
grep -rn "from app.application\|from app.infrastructure" app/domain/ && echo "VIOLATION: domain imports upper layer" || echo "OK"
```

通过标准：以上 grep 无匹配输出。

---

### Step 4 — 单元测试

```bash
pytest tests/unit -v --tb=short
```

通过标准：100% 通过，coverage ≥ 80%（核心 Agent 逻辑）。

---

### Step 5 — 集成测试

```bash
# 需要 Docker Compose 启动（PostgreSQL + Redis）
docker compose up -d db redis

pytest tests/integration -v --tb=short

docker compose down
```

通过标准：100% 通过。

---

### Step 6 — 全量覆盖率报告

```bash
pytest --cov=app tests/ --cov-report=term-missing --cov-fail-under=75
```

通过标准：整体覆盖率 ≥ 75%。

---

## 本地快速预检（提交前必跑）

```bash
# 一键执行所有检查
make ci

# 或逐步执行
ruff check app/ && \
mypy app/ --ignore-missing-imports && \
pytest tests/unit -q
```

---

## Makefile 参考

```makefile
.PHONY: ci lint type-check test test-all

lint:
    ruff check app/ --fix && ruff format app/

type-check:
    mypy app/ --ignore-missing-imports --strict

test:
    pytest tests/unit -v

test-all:
    pytest --cov=app tests/ --cov-report=term-missing --cov-fail-under=75

ci: lint type-check test
```

---

## GitHub Actions 配置

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, "feature/**"]
  pull_request:
    branches: [main]

jobs:
  ci:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: admin
          POSTGRES_PASSWORD: secret
          POSTGRES_DB: ai_interview_test
        ports: ["5432:5432"]
      redis:
        image: redis:7
        ports: ["6379:6379"]

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Lint
        run: ruff check app/ && ruff format --check app/

      - name: Type check
        run: mypy app/ --ignore-missing-imports --strict

      - name: Architecture compliance
        run: |
          ! grep -rn "from app.infrastructure" app/api/
          ! grep -rn "from app.application\|from app.infrastructure" app/domain/

      - name: Unit tests
        run: pytest tests/unit -v

      - name: Integration tests
        env:
          DATABASE_URL: postgresql+asyncpg://admin:secret@localhost:5432/ai_interview_test
          REDIS_URL: redis://localhost:6379
        run: pytest tests/integration -v

      - name: Coverage
        run: pytest --cov=app tests/ --cov-fail-under=75
```

---

## CI 输出格式

CI 完成后，将结果填入对应 Feature 的 `specs/AIP-xxx/changelog.md`：

```markdown
## CI: YYYY-MM-DD

| 检查项 | 结果 |
|---|---|
| Lint (ruff) | PASS / FAIL |
| Type check (mypy) | PASS / FAIL |
| 架构合规 | PASS / FAIL |
| 单元测试 | PASS (xx/xx) / FAIL |
| 集成测试 | PASS (xx/xx) / FAIL |
| 覆盖率 | xx% |

**结论**：Green / Red（阻断合并）
```

---

## 阻断规则

以下任一失败，**禁止合并**：

- `ruff check` 有 error
- `mypy` 有 error
- 架构合规检查有违规
- 单元测试有失败
- 整体覆盖率 < 75%

集成测试失败允许带注释合并，但必须在 `current/blockers.md` 记录原因。
