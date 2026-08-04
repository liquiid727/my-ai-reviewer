"""Markdown 解析器 —— 读取 .md 简历原文。

Markdown 本身已是结构化文本，LLM 可直接理解；解析器负责规范
换行符、去除行尾空白，并保留原文（含标题、列表、代码块等）。
"""

from backend.infrastructure.parsers.base import (
    BLOCK_HEADING,
    BLOCK_PARAGRAPH,
    ParsedResumeText,
    ResumeParser,
    TextBlock,
    read_text_with_fallback,
)


class MarkdownResumeParser(ResumeParser):
    """Markdown 简历解析器：原样返回规范化后的文本。"""

    @property
    def version(self) -> str:
        return "markdown-v1"

    def parse(self, file_path: str) -> ParsedResumeText:
        content = read_text_with_fallback(file_path)

        # 统一换行符为 \n，去除每行行尾空白，保留空行结构
        lines = [line.rstrip() for line in content.splitlines()]
        raw_text = "\n".join(lines).strip()

        # Markdown 原生结构：# 开头为标题，其余非空行为段落
        blocks: list[TextBlock] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                blocks.append(TextBlock(
                    type=BLOCK_HEADING,
                    text=stripped.lstrip("#").strip(),
                ))
            else:
                blocks.append(TextBlock(type=BLOCK_PARAGRAPH, text=stripped))

        return ParsedResumeText(
            raw_text=raw_text,
            page_count=None,
            blocks=blocks,
        )
