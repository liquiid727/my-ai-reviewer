"""简历文件解析器模块 —— 根据文件扩展名选择合适的解析器。"""

from backend.infrastructure.parsers.base import (
    ParsedResumeText,
    ResumeParser,
    read_text_with_fallback,
)
from backend.infrastructure.parsers.doc_parser import DocResumeParser
from backend.infrastructure.parsers.docx_parser import DocxResumeParser
from backend.infrastructure.parsers.html_parser import HtmlResumeParser
from backend.infrastructure.parsers.markdown_parser import MarkdownResumeParser
from backend.infrastructure.parsers.pdf_parser import PdfResumeParser
from backend.infrastructure.parsers.text_parser import TextResumeParser

# 文件扩展名 → 解析器类的映射
_PARSER_MAP: dict[str, type[ResumeParser]] = {
    ".pdf": PdfResumeParser,  # PDF（PyMuPDF）
    ".docx": DocxResumeParser,  # Word 2007+（python-docx）
    ".doc": DocResumeParser,  # 旧版 Word 二进制（LibreOffice 或尽力而为）
    ".txt": TextResumeParser,  # 纯文本
    ".md": MarkdownResumeParser,  # Markdown（保留原文结构）
    ".html": HtmlResumeParser,  # HTML 网页简历
    ".htm": HtmlResumeParser,  # HTML 网页简历（简写）
}

# 支持的所有文件扩展名
SUPPORTED_EXTENSIONS: set[str] = set(_PARSER_MAP)


def get_parser(ext: str) -> ResumeParser:
    """根据文件扩展名获取对应的解析器实例。"""
    ext = ext.lower()
    parser_cls = _PARSER_MAP.get(ext)
    if parser_cls is None:
        raise ValueError(f"Unsupported file extension: {ext}")
    return parser_cls()


__all__ = [
    "ParsedResumeText",
    "ResumeParser",
    "read_text_with_fallback",
    "get_parser",
    "SUPPORTED_EXTENSIONS",
    "DocResumeParser",
    "DocxResumeParser",
    "HtmlResumeParser",
    "MarkdownResumeParser",
    "PdfResumeParser",
    "TextResumeParser",
]
