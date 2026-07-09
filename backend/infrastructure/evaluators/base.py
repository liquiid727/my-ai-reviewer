"""简历评估器基类 —— 定义评估器抽象接口。"""

from abc import ABC, abstractmethod


class ResumeEvaluator(ABC):
    """简历评估器抽象基类：接收解析结果，返回评估报告。"""

    @abstractmethod
    async def evaluate(self, parsed_result: dict) -> dict:
        pass
