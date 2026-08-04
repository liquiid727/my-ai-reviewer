# Active Feature

**当前功能**：`RIP-001-resume-multiformat-parsers` / issue #038

**状态**：Implemented locally（待评审 / 发布）

**规格文件**：`specs/RIP-001-resume-multiformat-parsers/spec.md`

**任务文件**：`tasks/issues/issue-038-txt-md-encoding-fallback.md`

---

## 功能目标

完成 TXT / Markdown 编码兜底：

- UTF-8 / UTF-8 BOM 优先读取
- `charset-normalizer` 探测常见非 UTF-8 编码
- 探测失败时替换解码并记录 warning
- 同步更新解析器架构文档和单测
