# RIP-001 — Resume Multi-format Parsers

**Version**: v1.0
**Status**: Not Started
**Estimated**: 3-4 天
**Track**: Resume Intelligence Platform（PRD §4）
**Source**: `docs/prd/parser.md` §4；延伸 `tasks/spec-resume-input.md`（当前仅 PDF/DOCX 实现，抽取为 mock）

---

## 目标

补齐简历解析器，支持 PRD §4 要求的全部格式：**PDF、DOC、DOCX、HTML、Markdown、TXT**。当前仅实现 PDF（`pdf_parser.py`, pypdf）与 DOCX（`docx_parser.py`, python-docx），且抽取层（`llm_resume_extractor.py`）仍为按关键字的 mock。本 spec 聚焦"文本抽取层"的多格式覆盖，统一输出 `ParsedResumeText`，为下游 Extractor / Classifier 提供一致输入。

## 现状

- `infrastructure/parsers/base.py`：`ResumeParser(ABC)` + `ParsedResumeText(raw_text, page_count)`
- 已实现：`PdfResumeParser`、`DocxResumeParser`
- 缺失：DOC（旧版二进制）、HTML、Markdown、TXT 解析器
- `detect_file_type` 目前仅按扩展名粗略判断

## 技术栈

- DOC：`docx2txt` 或 `textract`（或 antiword 包装）
- HTML：`beautifulsoup4` + `html2text` 清洗正文
- Markdown：`markdown` / `marko` 转纯文本
- TXT：内置读取（编码探测 + `pathlib`）
- 类型探测：`python-magic` 或扩展名 + MIME 映射

## 接口/行为

- 新增 `DocResumeParser` / `HtmlResumeParser` / `MarkdownResumeParser` / `TxtResumeParser`，均继承 `ResumeParser`
- `detect_file_type` 工厂按扩展名 / MIME 路由到对应 Parser
- 统一返回 `ParsedResumeText(raw_text, page_count=None)`
- 不支持的格式抛已有 `UnsupportedFileFormatError`

## 验收标准

- [ ] `DocResumeParser` 解析 .doc 返回 `ParsedResumeText`
- [ ] `HtmlResumeParser` 去除 script/style，保留正文文本
- [ ] `MarkdownResumeParser` 解析 .md / .markdown
- [ ] `TxtResumeParser` 解析 .txt（编码容错）
- [ ] `detect_file_type` 支持 6 种格式；未知格式返回明确错误
- [ ] 单测覆盖每种 parser（fixture 样本）
- [ ] `POST /api/v1/resume/upload` 接受全部 6 种格式
