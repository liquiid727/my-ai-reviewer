"""纯文本解析器 —— 直接读取 .txt / .md 文件内容。"""

from backend.infrastructure.parsers.base import (
    ParsedResumeText,
    ResumeParser,
    blocks_from_text,
    read_text_with_fallback,
)


class TextResumeParser(ResumeParser):
    """纯文本文件解析器（支持 .txt 和 .md）。"""

    @property
    def version(self) -> str:
        return "text-v1"

    def parse(self, file_path: str) -> ParsedResumeText:
        raw_text = read_text_with_fallback(file_path)

        return ParsedResumeText(
            raw_text=raw_text,
            page_count=None,
            blocks=blocks_from_text(raw_text),
        )
