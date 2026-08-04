# RIP-001 — Resume Multi-format Parsers

**Version**: v1.1
**Status**: Implemented locally（待评审 / 发布）
**Estimated**: 3-4 天（主体和编码兜底已实现，待评审 / 发布）
**Track**: Resume Intelligence Platform（PRD §4）
**Source**: `tasks/prd-parser.md` §4；延伸 `tasks/spec-resume-input.md`；增量：`tasks/prd-resume-toolchain-increments.md`（US-007 / FR-13）

---

## 目标

补齐简历解析器，支持 PRD §4 要求的全部格式：**PDF、DOC、DOCX、HTML、Markdown、TXT**。六种格式均已接入 Parser 工厂并统一输出 `ParsedResumeText`，为下游 Extractor / Classifier 提供一致输入。本次增量补齐 TXT / Markdown 的非 UTF-8 编码兜底。

## 现状

- `infrastructure/parsers/base.py`：`ResumeParser(ABC)` + `ParsedResumeText(raw_text, page_count, blocks)`
- 已实现：`PdfResumeParser`、`DocxResumeParser`、`DocResumeParser`、`HtmlResumeParser`、`MarkdownResumeParser`、`TextResumeParser`
- Parser 工厂按扩展名路由，覆盖 `.pdf`、`.docx`、`.doc`、`.txt`、`.md`、`.html`、`.htm`
- TXT / Markdown 共用 `read_text_with_fallback`，支持 UTF-8、BOM、常见中文编码和替换解码

## 技术栈

- DOC：优先 LibreOffice `soffice` 转换，失败时提取可读文本片段
- DOCX：`python-docx` 提取段落和表格
- PDF：PyMuPDF 逐页提取文本并记录页码
- HTML：标准库 `html.parser` 清除不可见标签并提取正文
- Markdown：轻量自实现，保留标题、列表和代码块文本结构
- TXT：`charset-normalizer` 编码探测，最终以 `errors="replace"` 兜底
- 类型探测：扩展名映射（不引入额外 MIME 依赖）

## 接口/行为

- `DocResumeParser` / `HtmlResumeParser` / `MarkdownResumeParser` / `TextResumeParser` 均继承 `ResumeParser`
- `get_parser` 工厂按扩展名路由到对应 Parser
- 统一返回 `ParsedResumeText(raw_text, page_count=None, blocks=...)`
- 不支持的扩展名抛出明确的 `ValueError`

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

> 来源：`tasks/prd-resume-toolchain-increments.md` US-007 / FR-13。该增量已实现并由 TXT / Markdown 两个解析器共用。

## 设计

- 新增 `parsers/base.py:read_text_with_fallback(file_path) -> str`，两个 parser 共用：
  1. 优先 utf-8（含 BOM：utf-8-sig）
  2. 失败 → `charset_normalizer.from_path` 探测（覆盖 GBK / GB18030 / Big5）重读
  3. 仍失败 → `errors="replace"` 尽力解码，记 warning 日志，不阻断流水线
- 依赖：`charset-normalizer`（纯 Python，写入 `backend/pyproject.toml` 主依赖）
- 同步更新 `domain/resume/parse.md`：清理旧版设计笔记，改为当前 6 格式解析器真实架构（工厂路由 / blocks 模型 / 各 parser 技术选型）

## 增量验收标准

- [x] utf-8 / UTF-8 BOM / GBK / GB18030 fixture 样本解析结果一致（由单测临时 fixture 覆盖）
- [x] 探测失败时 `errors="replace"` 兜底不抛异常，记 warning
- [x] `domain/resume/parse.md` 更新为当前真实设计
- [ ] 全库 lint / mypy 通过（parser 范围 `ruff` / `mypy` 已通过；全库 `mypy` 仍有 35 个既有错误）
