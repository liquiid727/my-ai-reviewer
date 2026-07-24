"""PDF 解析器 —— 使用 PyMuPDF 提取 PDF 文件中的文本。"""

import pymupdf

from backend.infrastructure.parsers.base import (
    ParsedResumeText,
    ResumeParser,
    TextBlock,
    blocks_from_text,
)


class PdfResumeParser(ResumeParser):
    """PDF 文件解析器，逐页提取文本内容。"""

    @property
    def version(self) -> str:
        return "pdf-pymupdf-v1"

    def parse(self, file_path: str) -> ParsedResumeText:
        doc = pymupdf.open(file_path)  # type: ignore[no-untyped-call]
        try:
            # 逐页提取文本，页间用空行分隔，并按页生成带页码的结构块
            pages = [page.get_text() for page in doc]  # type: ignore[attr-defined]
            blocks: list[TextBlock] = []
            for page_num, page_text in enumerate(pages, start=1):
                blocks.extend(blocks_from_text(page_text, page=page_num))
            return ParsedResumeText(
                raw_text="\n\n".join(pages),
                page_count=len(pages),
                blocks=blocks,
            )
        finally:
            doc.close()  # type: ignore[no-untyped-call]
