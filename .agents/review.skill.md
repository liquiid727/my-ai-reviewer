# Review Skill

每个 Feature 完成后，对照此清单进行 Code Review。

---

## 通用检查项

### 架构
- [ ] DDD 分层没有跨层调用（api 只调用 application）
- [ ] 新增功能有对应的 domain 实体和 repository

### 代码质量
- [ ] 所有公开函数有类型注解
- [ ] 没有硬编码字符串（用常量或枚举）
- [ ] 没有硬编码配置（全走 env var）
- [ ] 异步函数正确使用 async/await（无 sync 阻塞）

### 数据库
- [ ] 有对应 Alembic 迁移文件
- [ ] 迁移可正向执行（`alembic upgrade head`）
- [ ] 敏感字段有加密或脱敏

### Agent
- [ ] Prompt 有 System + User 分离
- [ ] 结构化输出用 Pydantic 定义
- [ ] LLM 调用有 timeout 和错误处理

### 测试
- [ ] 核心 Agent 有单元测试（mock LLM）
- [ ] 主要 API 有集成测试
- [ ] 边界场景有测试覆盖

---

## Review 输出

填写到对应 Feature 的 `review.md` 文件，格式：

```markdown
## Review: YYYY-MM-DD

### 通过项
- xxx

### 需改进项
- [ ] xxx（优先级：高/中/低）

### 结论
Approved / Request Changes
```
