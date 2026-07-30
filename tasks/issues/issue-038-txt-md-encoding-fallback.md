# TXT/MD 编码兜底 + parse.md 文档更新

## Description

TXT/MD 解析器目前仅按 utf-8 读取，GBK 等非 UTF-8 文件会解析失败。新增三级编码兜底：utf-8-sig → charset-normalizer 探测重读 → `errors="replace"` 兜底并记录 warning。同步更新 `domain/resume/parse.md`（现为旧版设计笔记）以反映当前解析器实况。

PRD Reference: tasks/prd-resume-toolchain-increments.md US-007 / FR-13
SPEC Reference: specs/RIP-001-resume-multiformat-parsers/spec.md「增量设计（v1.1）：TXT/MD 编码兜底」

## Acceptance Criteria

- [ ] `backend/infrastructure/parsers/base.py` 新增 `read_text_with_fallback(file_path) -> str`
- [ ] 三级策略：utf-8-sig 直读 → `charset_normalizer.from_path` 探测重读 → `errors="replace"` + warning 日志
- [ ] TXT 与 MD 解析器统一改用该函数读取
- [ ] `charset-normalizer` 加入 backend 主依赖
- [ ] 更新 `backend/domain/resume/parse.md`：与现有 6 格式解析器实现对齐（含技术选型偏差说明）
- [ ] 单测：utf-8 / utf-8-sig(BOM) / GBK / 畸形字节四类 fixture 均能解析
- [ ] Lint / mypy 通过

## Dependencies

None

## Type

backend

## Priority

low
