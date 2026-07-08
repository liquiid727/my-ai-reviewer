from backend.infrastructure.parsers.base import ParsedResumeText, ResumeParser
from backend.infrastructure.parsers.docx_parser import DocxResumeParser
from backend.infrastructure.parsers.pdf_parser import PdfResumeParser
from backend.infrastructure.parsers.text_parser import TextResumeParser

_PARSER_MAP: dict[str, type[ResumeParser]] = {
    ".pdf": PdfResumeParser,
    ".docx": DocxResumeParser,
    ".doc": DocxResumeParser,
    ".txt": TextResumeParser,
    ".md": TextResumeParser,
}

SUPPORTED_EXTENSIONS: set[str] = set(_PARSER_MAP)


def get_parser(ext: str) -> ResumeParser:
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
