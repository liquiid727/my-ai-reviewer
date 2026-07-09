"""纯文本解析器 —— 直接读取 .txt / .md 文件内容。"""

from backend.infrastructure.parsers.base import ParsedResumeText, ResumeParser


class TextResumeParser(ResumeParser):
    """纯文本文件解析器（支持 .txt 和 .md）。"""

    @property
    def version(self) -> str:
        return "text-v1"

    def parse(self, file_path: str) -> ParsedResumeText:
        with open(file_path, encoding="utf-8") as f:
            raw_text = f.read()

        return ParsedResumeText(
            raw_text=raw_text,
            page_count=None,
        )
