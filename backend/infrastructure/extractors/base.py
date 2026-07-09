"""简历信息提取器基类 —— 定义提取器抽象接口。"""

from abc import ABC, abstractmethod


class ResumeExtractor(ABC):
    """简历信息提取器抽象基类：接收原始文本，返回结构化数据。"""
    version: str = "base"

    @abstractmethod
    async def extract(self, raw_text: str) -> dict:
        pass
