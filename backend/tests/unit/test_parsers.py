"""解析器单元测试 —— 覆盖新增的 HTML / Markdown / DOC 解析器与扩展名映射。"""

from backend.infrastructure.parsers import (
    DocResumeParser,
    HtmlResumeParser,
    MarkdownResumeParser,
    TextResumeParser,
    get_parser,
)
from backend.infrastructure.parsers.docx_parser import DocxResumeParser
from backend.infrastructure.parsers.pdf_parser import PdfResumeParser

HTML_SAMPLE = """
<html><head><title>忽略</title></head>
<body>
  <script>var secret = 'should_not_appear';</script>
  <h1>张三 的简历</h1>
  <p>高级后端工程师</p>
  <p>技能：Python, FastAPI</p>
  <ul><li>Redis</li><li>PostgreSQL</li></ul>
</body></html>
"""

MARKDOWN_SAMPLE = """# 李四
## 工作经历
- 公司 A：后端开发
- 公司 B：基础架构
"""


def test_get_parser_mapping():
    assert isinstance(get_parser(".pdf"), PdfResumeParser)
    assert isinstance(get_parser(".docx"), DocxResumeParser)
    assert isinstance(get_parser(".doc"), DocResumeParser)
    assert isinstance(get_parser(".txt"), TextResumeParser)
    assert isinstance(get_parser(".md"), MarkdownResumeParser)
    assert isinstance(get_parser(".html"), HtmlResumeParser)
    assert isinstance(get_parser(".htm"), HtmlResumeParser)


def test_html_parser_strips_scripts_and_extracts_text(tmp_path):
    f = tmp_path / "resume.html"
    f.write_text(HTML_SAMPLE, encoding="utf-8")

    result = HtmlResumeParser().parse(str(f))

    assert "should_not_appear" not in result.raw_text
    assert "张三 的简历" in result.raw_text
    assert "高级后端工程师" in result.raw_text
    assert "Python, FastAPI" in result.raw_text
    assert "Redis" in result.raw_text
    assert result.page_count is None


def test_markdown_parser_preserves_structure(tmp_path):
    f = tmp_path / "resume.md"
    f.write_text(MARKDOWN_SAMPLE, encoding="utf-8")

    result = MarkdownResumeParser().parse(str(f))

    assert "# 李四" in result.raw_text
    assert "## 工作经历" in result.raw_text
    assert "公司 A：后端开发" in result.raw_text
    assert result.page_count is None


def test_doc_parser_best_effort_recovers_text(tmp_path):
    # 模拟旧版 .doc 二进制流：可读文本夹杂空字节
    blob = b"\x00\x00Some Company Resume\x00\x01Python Developer\x00\x02"
    f = tmp_path / "legacy.doc"
    f.write_bytes(blob)

    result = DocResumeParser().parse(str(f))

    assert "Some Company Resume" in result.raw_text
    assert "Python Developer" in result.raw_text
    assert result.page_count is None


def test_text_parser_reads_plain_text(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("纯文本简历内容", encoding="utf-8")

    result = TextResumeParser().parse(str(f))
    assert "纯文本简历内容" in result.raw_text
