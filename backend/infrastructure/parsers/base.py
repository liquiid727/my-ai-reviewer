"""文件解析器基类 —— 定义解析结果数据结构和解析器抽象接口。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ParsedResumeText:
    """解析结果：包含提取的原始文本和页数信息。"""
    raw_text: str                    # 提取的原始文本
    page_count: int | None = None    # 页数（PDF 有值，其他格式为 None）


class ResumeParser(ABC):
    """文件解析器抽象基类。"""

    @property
    @abstractmethod
    def version(self) -> str: ...

    @abstractmethod
    def parse(self, file_path: str) -> ParsedResumeText: ...
