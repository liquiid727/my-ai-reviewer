"""内置参考简历模板 —— 提供开箱即用的结构化简历范本。

每个参考模板由两部分组成：
- 同目录下的 Markdown 源文件（人类可读的原始范本，保持可追溯）
- 对应的 Python 模块（把范本转换为可编辑的 ResumeDraft 结构）

新增模板时在 _REGISTRY 中注册即可被 API 自动发现。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from backend.domain.resume_builder.reference_templates.ai_application_engineer import (
    build_ai_application_engineer_draft,
)
from backend.domain.resume_builder.schemas import ResumeDraft


@dataclass(frozen=True)
class ReferenceTemplate:
    """一个内置参考模板的元信息与草稿构建器。"""

    key: str  # 唯一标识（URL 安全）
    name: str  # 展示名称
    description: str  # 一句话说明
    tags: tuple[str, ...]  # 方向标签（前端展示用）
    build_draft: Callable[[], ResumeDraft]  # 构建全新草稿（每次调用返回独立副本）


_REGISTRY: dict[str, ReferenceTemplate] = {
    "ai_application_engineer": ReferenceTemplate(
        key="ai_application_engineer",
        name="AI 应用开发工程师",
        description="面向 AI 应用开发 / AI 全栈方向的完整简历范本，覆盖 LLM、RAG、Agent 与后端工程经验。",
        tags=("AI 应用", "Go/Python 后端", "RAG/Agent"),
        build_draft=build_ai_application_engineer_draft,
    ),
}


def list_reference_templates() -> list[ReferenceTemplate]:
    """返回全部内置参考模板（注册顺序）。"""
    return list(_REGISTRY.values())


def get_reference_template(key: str) -> ReferenceTemplate | None:
    """按 key 查找参考模板，不存在返回 None。"""
    return _REGISTRY.get(key)
