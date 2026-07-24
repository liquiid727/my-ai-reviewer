# RIP-001 Tasks

**Feature**: Resume Multi-format Parsers
**Status**: Not Started
**Depends on**: —

---

## Task 列表

### T1 — DOC 解析器
- [ ] 引入 `docx2txt` / `textract` 依赖（写入 `backend/pyproject.toml`）
- [ ] 实现 `DocResumeParser.parse` → `ParsedResumeText`
- [ ] 处理旧版 .doc 二进制与编码

### T2 — HTML 解析器
- [ ] 引入 `beautifulsoup4` + `html2text`
- [ ] 去除 script/style/nav，提取正文
- [ ] 实现 `HtmlResumeParser`

### T3 — Markdown 解析器
- [ ] 引入 `markdown` / `marko`
- [ ] 实现 `MarkdownResumeParser`（MD → 纯文本）

### T4 — TXT 解析器
- [ ] 实现 `TxtResumeParser`，编码探测（utf-8 / chardet 兜底）

### T5 — 类型探测与工厂路由
- [ ] `detect_file_type` 扩展名 + MIME 映射，覆盖 6 种格式
- [ ] 未知格式 → `UnsupportedFileFormatError`
- [ ] 注册到 Parser 工厂

### T6 — 测试与集成
- [ ] 各 parser 单测（fixture 样本）
- [ ] `POST /api/v1/resume/upload` 接受全部格式
- [ ] 更新 `domain/resume/parse.md` 文档

---

## 依赖顺序

T1、T2、T3、T4 可并行 → T5 → T6
