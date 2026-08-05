# Image / OCR Resume Parser

## Description

PRD §4「后续支持」列出图片（OCR）。当前解析器不支持图片/扫描件。新增图片 parser，通过 OCR 提取文本并接入现有 pipeline，同时在 ResumeDocument 记录 OCR 状态。

PRD Reference: tasks/prd-parser.md §4

## Acceptance Criteria

- [ ] 新增 `backend/infrastructure/parsers/image_parser.py`（OCR，如 tesseract/云 OCR 抽象）
- [ ] `_PARSER_MAP` 注册 .png/.jpg/.jpeg，上传白名单同步
- [ ] `FileModel`/ResumeDocument 记录 `ocr_status`
- [ ] OCR 失败降级与错误可追溯
- [ ] 单测（可 mock OCR 后端）
- [ ] Typecheck 通过

## Dependencies

Issue #28

## Type

backend

## Priority

low
