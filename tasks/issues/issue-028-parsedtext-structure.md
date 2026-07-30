# Structured ParsedText Layers (Paragraph / Heading / Block / Page)

## Description

PRD §3.1 要求 ResumeParsedText 支持 Raw Text / Paragraph / Heading / Block / Page 层级，以保证 Parser 可升级与精确定位。当前 `ParsedResumeText` 仅有 `raw_text` + `page_count`。引入结构化块模型，各 parser 在能力范围内填充。

PRD Reference: tasks/prd-parser.md §3.1

## Acceptance Criteria

- [ ] `backend/infrastructure/parsers/base.py`：新增 `TextBlock`(type: paragraph/heading/block, text, page) 与 `ParsedResumeText.blocks: list[TextBlock]`
- [ ] PDF/DOCX/HTML/Markdown parser 尽力填充 blocks（heading 识别 + page 归属），txt/doc 降级只填 paragraph
- [ ] `raw_text` 保持向后兼容（由 blocks 拼接或原样）
- [ ] blocks 可选落库到 `ResumeParsedText` 存储（JSONB）
- [ ] 单测覆盖各 parser 的 blocks 输出
- [ ] Typecheck 通过

## Dependencies

None

## Type

backend

## Priority

medium
