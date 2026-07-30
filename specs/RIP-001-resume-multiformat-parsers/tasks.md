# RIP-001 Tasks

**Feature**: Resume Multi-format Parsers
**Status**: Done（残留：TXT 编码兜底、parse.md 文档更新）
**Depends on**: —

---

## Task 列表

### T1 — DOC 解析器
- [x] ~~引入 `docx2txt` / `textract` 依赖~~（偏差：改用 LibreOffice `soffice` 转换 + 尽力而为解码，零新依赖）
- [x] 实现 `DocResumeParser.parse` → `ParsedResumeText`
- [x] 处理旧版 .doc 二进制与编码（`_try_libreoffice_convert` + `_best_effort_text` 兜底）

### T2 — HTML 解析器
- [x] ~~引入 `beautifulsoup4` + `html2text`~~（偏差：改用标准库 `html.parser`，零新依赖）
- [x] 去除 script/style/nav，提取正文（`_HtmlTextExtractor`）
- [x] 实现 `HtmlResumeParser`（.html / .htm）

### T3 — Markdown 解析器
- [x] ~~引入 `markdown` / `marko`~~（偏差：自实现 MD → 纯文本，零新依赖）
- [x] 实现 `MarkdownResumeParser`

### T4 — TXT 解析器
- [x] 实现 `TextResumeParser`
- [ ] 编码探测（当前仅 utf-8，chardet 兜底未做）

### T5 — 类型探测与工厂路由
- [x] 扩展名 + MIME 映射，覆盖 7 个扩展名（含 .htm；`ALLOWED_EXTENSIONS` / `_MIME_MAP`）
- [x] 未知格式 → 明确错误（偏差：`get_parser` 抛 `ValueError` 而非 `UnsupportedFileFormatError`）
- [x] 注册到 Parser 工厂（`_PARSER_MAP` + `get_parser`）

### T6 — 测试与集成
- [x] 各 parser 单测（`tests/unit/test_parsers.py`）
- [x] `POST /api/v1/resume/upload` 接受全部格式
- [ ] 更新 `domain/resume/parse.md` 文档（仍是旧版设计笔记）

---

## 依赖顺序

T1、T2、T3、T4 可并行 → T5 → T6
