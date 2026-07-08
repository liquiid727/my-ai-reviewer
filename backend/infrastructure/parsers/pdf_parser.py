import pymupdf

from backend.infrastructure.parsers.base import ParsedResumeText, ResumeParser


class PdfResumeParser(ResumeParser):
    @property
    def version(self) -> str:
        return "pdf-pymupdf-v1"

    def parse(self, file_path: str) -> ParsedResumeText:
        doc = pymupdf.open(file_path)
        try:
            pages = [page.get_text() for page in doc]  # type: ignore[attr-defined]
            return ParsedResumeText(
                raw_text="\n\n".join(pages),
                page_count=len(pages),
            )
        finally:
            doc.close()
