# Agent Workflow

## 标准工作流程

### 1. 加载上下文
按 `project-context.md` 定义的顺序加载文件，控制在 10 个以内。

### 2. 确认当前任务
读取 `current/active-tasks.md` 和 `specs/AIP-xxx/tasks.md`，
找到状态为 `[ ]`（未完成）的第一个任务。

### 3. 执行任务
遵循 `design/coding-guidelines.md` 规范实现代码。

### 4. 更新状态
- 任务完成 → 在 `specs/AIP-xxx/tasks.md` 中将 `[ ]` 改为 `[x]`
- 发现阻塞 → 写入 `current/blockers.md`
- 阶段完成 → 更新 `current/project-status.md`

### 5. 更新 Changelog
每次有实质性变更，在 `specs/AIP-xxx/changelog.md` 追加记录。

---

## 新功能开发流程

```
1. 在 specs/_draft/ 起草 spec
2. 评审通过后移动到 specs/AIP-xxx/
3. 补全 tasks.md + tests.md
4. 更新 current/active-feature.md
5. 开始开发
6. 开发完成后填写 review.md
7. Review 通过后更新 project-status.md
```

---

## Feature ID 分配

格式：`AIP-{三位数字}-{短名称}`

当前已分配：
- AIP-001 ~ AIP-008（见 specs/roadmap.md）

新增功能从 AIP-009 开始。
