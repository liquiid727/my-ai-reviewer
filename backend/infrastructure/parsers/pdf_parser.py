"""PDF 解析器 —— 使用 PyMuPDF 提取 PDF 文件中的文本。"""

import pymupdf

from backend.infrastructure.parsers.base import ParsedResumeText, ResumeParser


class PdfResumeParser(ResumeParser):
    """PDF 文件解析器，逐页提取文本内容。"""

    @property
    def version(self) -> str:
        return "pdf-pymupdf-v1"

    def parse(self, file_path: str) -> ParsedResumeText:
        doc = pymupdf.open(file_path)
        try:
            # 逐页提取文本，页间用空行分隔
            pages = [page.get_text() for page in doc]  # type: ignore[attr-defined]
            return ParsedResumeText(
                raw_text="\n\n".join(pages),
                page_count=len(pages),
            )
        finally:
            doc.close()
