# TXT/MD 编码兜底 + parse.md 文档更新

**Status**: Implemented locally（待评审 / 发布）

## Description

TXT/MD 解析器此前仅按 utf-8 读取，GBK 等非 UTF-8 文件会解析失败。本 issue 新增三级编码兜底：utf-8-sig → charset-normalizer 探测重读 → `errors="replace"` 兜底并记录 warning，并将 `domain/resume/parse.md` 更新为当前解析器实况。

PRD Reference: tasks/prd-resume-toolchain-increments.md US-007 / FR-13
SPEC Reference: specs/RIP-001-resume-multiformat-parsers/spec.md「增量设计（v1.1）：TXT/MD 编码兜底」

## Acceptance Criteria

- [x] `backend/infrastructure/parsers/base.py` 新增 `read_text_with_fallback(file_path) -> str`
- [x] 三级策略：utf-8-sig 直读 → `charset_normalizer.from_path` 探测重读 → `errors="replace"` + warning 日志
- [x] TXT 与 MD 解析器统一改用该函数读取
- [x] `charset-normalizer` 加入 backend 主依赖
- [x] 更新 `backend/domain/resume/parse.md`：与现有 6 格式解析器实现对齐（含技术选型偏差说明）
- [x] 单测：utf-8 / utf-8-sig(BOM) / GBK / 畸形字节四类 fixture 均能解析
- [ ] 全库 lint / mypy 通过（本次 parser 范围 `ruff` / `mypy` 已通过；全库 `mypy` 仍有 35 个既有错误）

## Evidence

- 实现：`backend/infrastructure/parsers/base.py`
- 调用方：`backend/infrastructure/parsers/text_parser.py`、`markdown_parser.py`
- 单测：`backend/tests/unit/test_parsers.py`
- 说明：`backend/domain/resume/parse.md`
- 验证：parser 单测 13 passed；后端单元测试 134 passed；后端 `ruff` 全量通过
- 已知阻塞：全库 `mypy` 的既有错误集中在 imaging 可选依赖、Celery 和测试假 session

## Dependencies

None

## Type

backend

## Priority

low
