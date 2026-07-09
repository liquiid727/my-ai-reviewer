# Resume Text Extraction Service

## Description

实现简历文本提取服务，支持 PDF（PyMuPDF）、DOCX（python-docx）、TXT/MD 格式。遵循 `parse.md` 中已有的 ABC + 版本号模式。从 MinIO 下载文件，提取原始文本，保存到 resumes 表。

PRD Reference: US-003
SPEC Reference: Section 5.2

## Acceptance Criteria

- [ ] `backend/infrastructure/parsers/base.py`：`ParsedResumeText` 数据类 + `ResumeParser` ABC（含 version 属性）
- [ ] `backend/infrastructure/parsers/pdf_parser.py`：使用 PyMuPDF（`pymupdf`）提取 PDF 全部页面文本，保留段落结构，返回 page_count
- [ ] `backend/infrastructure/parsers/docx_parser.py`：使用 python-docx 提取段落和表格内容
- [ ] `backend/infrastructure/parsers/text_parser.py`：直接读取 TXT / Markdown 原始文本
- [ ] 每个 Parser 有独立的 `version` 字符串（如 "pdf-pymupdf-v1"）
- [ ] 根据文件扩展名自动选择 Parser
- [ ] 从 MinIO 下载文件到临时路径，解析后清理临时文件
- [ ] 提取结果保存到 `resumes.raw_text`
- [ ] page_count 保存到 `files.page_count`
- [ ] parser_version 保存到 `resumes.parser_version`
- [ ] 解析成功 → status 更新为 `text_parsed`
- [ ] 解析失败 → status 更新为 `failed`，错误信息写入 `resumes.parse_error`
- [ ] 空白 PDF（无文字层）→ 检测 raw_text 为空，标记失败
- [ ] `backend/domain/resume/services.py` 封装文本提取逻辑
- [ ] Typecheck 通过

## Dependencies

Issue #3

## Type

backend

## Priority

P0
