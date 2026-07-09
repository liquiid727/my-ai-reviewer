"""DOCX 解析器 —— 使用 python-docx 提取 Word 文档中的文本。"""

from docx import Document

from backend.infrastructure.parsers.base import ParsedResumeText, ResumeParser


class DocxResumeParser(ResumeParser):
    """Word 文档解析器，提取段落文本和表格内容。"""

    @property
    def version(self) -> str:
        return "docx-python-docx-v1"

    def parse(self, file_path: str) -> ParsedResumeText:
        doc = Document(file_path)

        parts: list[str] = []

        # 提取所有段落文本
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:
                parts.append(text)

        # 提取表格内容（简历中常用表格排版）
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))

        return ParsedResumeText(
            raw_text="\n".join(parts),
            page_count=None,    # DOCX 格式无法直接获取页数
        )
