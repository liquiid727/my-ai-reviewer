"""解析器单元测试 —— 覆盖六种格式、编码兜底和扩展名映射。"""

import codecs
import logging

import pytest

import backend.infrastructure.parsers.base as parser_base
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

LEGACY_TEXT = (
    "张三\n"
    "高级后端工程师\n"
    "熟悉 Python、Redis、PostgreSQL、分布式系统\n"
) * 8


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


@pytest.mark.parametrize("parser_cls", [TextResumeParser, MarkdownResumeParser])
def test_text_parsers_strip_utf8_bom(tmp_path, parser_cls):
    f = tmp_path / "resume.txt"
    f.write_bytes(codecs.BOM_UTF8 + "张三\nPython".encode("utf-8"))

    result = parser_cls().parse(str(f))

    assert result.raw_text.startswith("张三")
    assert "Python" in result.raw_text
    assert "\ufeff" not in result.raw_text


@pytest.mark.parametrize("parser_cls", [TextResumeParser, MarkdownResumeParser])
@pytest.mark.parametrize("encoding", ["gbk", "gb18030"])
def test_text_parsers_detect_legacy_chinese_encodings(tmp_path, parser_cls, encoding):
    f = tmp_path / "resume.txt"
    f.write_bytes(LEGACY_TEXT.encode(encoding))

    result = parser_cls().parse(str(f))

    assert "高级后端工程师" in result.raw_text
    assert "分布式系统" in result.raw_text


@pytest.mark.parametrize("parser_cls", [TextResumeParser, MarkdownResumeParser])
def test_text_parsers_replace_bytes_when_encoding_detection_fails(
    tmp_path, monkeypatch, caplog, parser_cls
):
    f = tmp_path / "malformed.txt"
    f.write_bytes(b"Resume\xff\xfe\xfa\xfb")
    monkeypatch.setattr(parser_base.charset_normalizer, "from_path", lambda _: [])

    with caplog.at_level(logging.WARNING, logger=parser_base.__name__):
        result = parser_cls().parse(str(f))

    assert "Resume" in result.raw_text
    assert "\ufffd" in result.raw_text
    assert "replacement decoding" in caplog.text
