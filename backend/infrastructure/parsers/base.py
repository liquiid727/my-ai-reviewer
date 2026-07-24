"""文件解析器基类 —— 定义解析结果数据结构和解析器抽象接口。"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# 块类型：段落 / 标题 / 通用块
BLOCK_PARAGRAPH = "paragraph"
BLOCK_HEADING = "heading"
BLOCK_GENERIC = "block"


@dataclass
class TextBlock:
    """结构化文本块：解析器在能力范围内产出的最小语义单元。"""
    type: str = BLOCK_PARAGRAPH      # paragraph / heading / block
    text: str = ""                   # 块文本
    page: int | None = None          # 所在页码（PDF 有值，其他为 None）


@dataclass
class ParsedResumeText:
    """解析结果：包含提取的原始文本、页数信息与结构化文本块。"""
    raw_text: str                                     # 提取的原始文本
    page_count: int | None = None                     # 页数（PDF 有值，其他格式为 None）
    blocks: list[TextBlock] = field(default_factory=list)  # 结构化文本块（Paragraph/Heading/Block/Page）


# 标题启发式：短行（<40 字符）、不以句末标点结尾、且不含明显句子结构
_SENTENCE_END = re.compile(r"[.。!！?？,，;；:：]\s*$")


def is_heading_line(line: str) -> bool:
    """基于启发式判断一行文本是否像标题。"""
    stripped = line.strip()
    if not stripped or len(stripped) > 40:
        return False
    if _SENTENCE_END.search(stripped):
        return False
    # 全大写英文短语，或常见简历分区词
    return True


def blocks_from_text(text: str, page: int | None = None) -> list[TextBlock]:
    """将纯文本按空行切分为段落块，并对疑似标题行标注 heading。

    供无原生结构信息的解析器（txt/doc/pdf 单页）复用。
    """
    blocks: list[TextBlock] = []
    for chunk in re.split(r"\n\s*\n", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = [ln for ln in chunk.splitlines() if ln.strip()]
        # 单行且像标题 → heading，否则整段作为 paragraph
        if len(lines) == 1 and is_heading_line(lines[0]):
            blocks.append(TextBlock(type=BLOCK_HEADING, text=lines[0].strip(), page=page))
        else:
            blocks.append(TextBlock(type=BLOCK_PARAGRAPH, text=chunk, page=page))
    return blocks


class ResumeParser(ABC):
    """文件解析器抽象基类。"""

    @property
    @abstractmethod
    def version(self) -> str: ...

    @abstractmethod
    def parse(self, file_path: str) -> ParsedResumeText: ...
