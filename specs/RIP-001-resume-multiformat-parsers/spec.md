# RIP-001 — Resume Multi-format Parsers

**Version**: v1.1
**Status**: Done（残留见 tasks.md：TXT 编码兜底、parse.md 文档）
**Estimated**: 3-4 天（已完成主体；残留编码兜底约 0.5 天）
**Track**: Resume Intelligence Platform（PRD §4）
**Source**: `tasks/prd-parser.md` §4；延伸 `tasks/spec-resume-input.md`；增量：`tasks/prd-resume-toolchain-increments.md`（US-007 / FR-13）

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

- [x] `DocResumeParser` 解析 .doc 返回 `ParsedResumeText`（LibreOffice 转换 + 兜底解码）
- [x] `HtmlResumeParser` 去除 script/style，保留正文文本（标准库 `html.parser`）
- [x] `MarkdownResumeParser` 解析 .md
- [x] `TextResumeParser` 解析 .txt（编码容错见下方增量设计）
- [x] 工厂路由覆盖 7 个扩展名；未知格式返回明确错误（`ValueError`）
- [x] 单测覆盖每种 parser（`tests/unit/test_parsers.py`）
- [x] `POST /api/v1/resume/upload` 接受全部 6 种格式

---

# 增量设计（v1.1）：TXT/MD 编码兜底

> 来源：`tasks/prd-resume-toolchain-increments.md` US-007 / FR-13。现状：`TextResumeParser` / `MarkdownResumeParser` 仅 `encoding="utf-8"` 直读，GBK 等编码文件抛 `UnicodeDecodeError` 导致解析失败。

## 设计

- 新增 `parsers/base.py:read_text_with_fallback(file_path) -> str`，两个 parser 共用：
  1. 优先 utf-8（含 BOM：utf-8-sig）
  2. 失败 → `charset_normalizer.from_path` 探测（覆盖 GBK / GB18030 / Big5）重读
  3. 仍失败 → `errors="replace"` 尽力解码，记 warning 日志，不阻断流水线
- 依赖：`charset-normalizer`（纯 Python，写入 `backend/pyproject.toml` 主依赖）
- 同步更新 `domain/resume/parse.md`：清理旧版设计笔记，改为当前 6 格式解析器真实架构（工厂路由 / blocks 模型 / 各 parser 技术选型）

## 增量验收标准

- [ ] utf-8 / GBK / GB18030 fixture 样本解析结果一致（`tests/fixtures/` 新增样本）
- [ ] 探测失败时 `errors="replace"` 兜底不抛异常，记 warning
- [ ] `domain/resume/parse.md` 更新为当前真实设计
- [ ] lint / mypy 通过，现有 parser 单测零回归
