from backend.infrastructure.parsers.base import ParsedResumeText, ResumeParser


class TextResumeParser(ResumeParser):
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
