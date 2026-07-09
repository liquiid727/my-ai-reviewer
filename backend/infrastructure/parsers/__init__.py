"""简历文件解析器模块 —— 根据文件扩展名选择合适的解析器。"""

from backend.infrastructure.parsers.base import ParsedResumeText, ResumeParser
from backend.infrastructure.parsers.docx_parser import DocxResumeParser
from backend.infrastructure.parsers.pdf_parser import PdfResumeParser
from backend.infrastructure.parsers.text_parser import TextResumeParser

# 文件扩展名 → 解析器类的映射
_PARSER_MAP: dict[str, type[ResumeParser]] = {
    ".pdf": PdfResumeParser,
    ".docx": DocxResumeParser,
    ".doc": DocxResumeParser,
    ".txt": TextResumeParser,
    ".md": TextResumeParser,
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
    "get_parser",
    "SUPPORTED_EXTENSIONS",
]
