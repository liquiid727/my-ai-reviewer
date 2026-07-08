from docx import Document

from backend.infrastructure.parsers.base import ParsedResumeText, ResumeParser


class DocxResumeParser(ResumeParser):
    @property
    def version(self) -> str:
        return "docx-python-docx-v1"

    def parse(self, file_path: str) -> ParsedResumeText:
        doc = Document(file_path)

        parts: list[str] = []

        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:
                parts.append(text)

        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))

        return ParsedResumeText(
            raw_text="\n".join(parts),
            page_count=None,
        )
