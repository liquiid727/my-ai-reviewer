# Active Tasks

**Feature**: RIP-001 / issue #038

**Last Updated**: 2026-08-02

---

## 进行中

_（实现已完成，等待测试、评审和发布）_

---

## 已完成

- `read_text_with_fallback` 及 TXT / Markdown 接入
- `charset-normalizer` 主依赖声明
- UTF-8、BOM、GBK、GB18030、畸形字节测试
- `backend/domain/resume/parse.md` 更新
- parser 范围 `ruff` / `mypy` 通过；全库 `mypy` 阻塞待后续清理

## 后续

1. 评审并发布 issue #038
2. 处理 issue #030 OCR parser
3. 处理 issue #031 平台导出 parser
