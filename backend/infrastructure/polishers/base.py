"""简历润色器基类 —— 定义润色器抽象接口。"""

from abc import ABC, abstractmethod

from backend.domain.resume.enums import ResumeSectionType
from backend.domain.resume_builder.schemas import PolishResult


class ResumePolisher(ABC):
    """简历润色器抽象基类：接收一组要点，返回润色后的建议（保留原文）。"""

    version: str = "base"

    @abstractmethod
    async def polish(
        self,
        section_type: ResumeSectionType,
        items: list[str],
        context: str | None = None,
    ) -> PolishResult:
        """对某区块的一组要点进行润色，返回原文与建议供逐条接受。"""
