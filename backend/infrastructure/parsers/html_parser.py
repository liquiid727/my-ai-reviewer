"""HTML 解析器 —— 使用标准库 html.parser 提取可见文本。

不依赖任何第三方库：剥离 <script>/<style>/<head> 等不可见内容，
将块级元素渲染为换行，保留简历正文可读文本。
"""

import html
import re
from html.parser import HTMLParser

from backend.infrastructure.parsers.base import (
    BLOCK_HEADING,
    BLOCK_PARAGRAPH,
    ParsedResumeText,
    ResumeParser,
    TextBlock,
)

# 视为「块级」的标签：遇到时插入换行，帮助还原段落结构
_BLOCK_TAGS = {
    "p", "div", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "li", "tr", "section", "article", "header", "footer", "ul", "ol",
    "table", "blockquote", "pre",
}
# 标题标签
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
# 完全跳过的标签（其可见文本无意义）
_SKIP_TAGS = {"script", "style", "head", "meta", "link", "title", "noscript"}


class _HtmlTextExtractor(HTMLParser):
    """逐标签收集可见文本，块级标签处换行，并记录标题块。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0
        self.blocks: list[TextBlock] = []
        self._heading_depth = 0
        self._heading_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag in _HEADING_TAGS:
            self._heading_depth += 1
            self._heading_buf = []
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in _HEADING_TAGS and self._heading_depth > 0:
            self._heading_depth -= 1
            heading_text = " ".join(self._heading_buf).strip()
            if heading_text:
                self.blocks.append(TextBlock(type=BLOCK_HEADING, text=heading_text))
            self._heading_buf = []
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._parts.append(data.strip())
            if self._heading_depth > 0:
                self._heading_buf.append(data.strip())
            else:
                self.blocks.append(TextBlock(type=BLOCK_PARAGRAPH, text=data.strip()))

    def get_text(self) -> str:
        raw = "".join(self._parts)
        # 折叠多余空行，保留结构
        return re.sub(r"\n{3,}", "\n\n", raw).strip()


class HtmlResumeParser(ResumeParser):
    """HTML 简历解析器：从网页/HTML 简历中抽取纯文本。"""

    @property
    def version(self) -> str:
        return "html-stdlib-v1"

    def parse(self, file_path: str) -> ParsedResumeText:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            html_content = f.read()

        extractor = _HtmlTextExtractor()
        extractor.feed(html_content)
        raw_text = html.unescape(extractor.get_text())

        return ParsedResumeText(
            raw_text=raw_text,
            page_count=None,  # HTML 无页码概念
            blocks=extractor.blocks,
        )
