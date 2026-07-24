# Platform Export Parsers (LinkedIn / Boss / 拉勾)

## Description

PRD §4「后续支持」列出 LinkedIn / Boss / 拉勾 导出格式。这些导出通常为结构化 HTML/PDF/JSON，直通通用 parser 会丢失结构。新增来源识别与专用适配器，映射到统一 CandidateProfile。

PRD Reference: docs/prd/parser.md §4

## Acceptance Criteria

- [ ] 来源识别（文件名/内容特征）判定 LinkedIn/Boss/拉勾
- [ ] 各来源适配器将导出内容映射为结构化 profile 输入（复用 §5 抽取或专用解析）
- [ ] `FileModel` 记录 `source`（文件来源）
- [ ] 无法识别时回退到通用 parser
- [ ] 单测覆盖各来源样例
- [ ] Typecheck 通过

## Dependencies

Issue #23

## Type

backend

## Priority

low
