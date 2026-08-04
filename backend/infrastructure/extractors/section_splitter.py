"""简历 Section 切分器 —— 基于标题启发式将文本块切分为语义区块。

独立于 LLM 抽取：直接消费解析阶段产出的结构化文本块（TextBlock），
按标题关键词映射到 PRD §3.1/§4 要求的 8 类 Section，可单独测试。
"""

from dataclasses import dataclass, field
from typing import Any

from backend.domain.resume.enums import ResumeSectionType
from backend.infrastructure.parsers.base import BLOCK_HEADING, TextBlock, is_heading_line

# 标题关键词 → Section 类型映射（中英文）。匹配时对标题做小写归一后子串匹配。
_SECTION_KEYWORDS: list[tuple[ResumeSectionType, tuple[str, ...]]] = [
    (
        ResumeSectionType.BASIC_INFO,
        (
            "基本信息",
            "个人信息",
            "个人资料",
            "联系方式",
            "basic info",
            "basic information",
            "personal information",
            "personal details",
            "contact",
        ),
    ),
    (
        ResumeSectionType.EDUCATION,
        (
            "教育背景",
            "教育经历",
            "学历",
            "教育",
            "education",
            "academic",
        ),
    ),
    (
        ResumeSectionType.WORK_EXPERIENCE,
        (
            "工作经历",
            "工作经验",
            "职业经历",
            "实习经历",
            "work experience",
            "employment",
            "professional experience",
            "experience",
        ),
    ),
    (
        ResumeSectionType.PROJECT_EXPERIENCE,
        (
            "项目经历",
            "项目经验",
            "项目",
            "project experience",
            "projects",
            "project",
        ),
    ),
    (
        ResumeSectionType.SKILLS,
        (
            "专业技能",
            "技术栈",
            "技能",
            "skills",
            "technical skills",
            "skill",
        ),
    ),
    (
        ResumeSectionType.CERTIFICATES,
        (
            "资格证书",
            "证书",
            "certificates",
            "certifications",
            "certificate",
        ),
    ),
    (
        ResumeSectionType.AWARDS,
        (
            "获奖经历",
            "所获奖项",
            "奖项",
            "荣誉",
            "获奖",
            "awards",
            "honors",
            "honours",
        ),
    ),
    (
        ResumeSectionType.SELF_EVALUATION,
        (
            "自我评价",
            "自我介绍",
            "个人评价",
            "个人总结",
            "self evaluation",
            "self-evaluation",
            "about me",
            "summary",
            "profile",
        ),
    ),
]


@dataclass
class ResumeSection:
    """一个语义区块的切分结果。"""

    section_type: ResumeSectionType
    title: str
    raw_text: str
    blocks: list[TextBlock] = field(default_factory=list)


def _match_section_type(title: str) -> ResumeSectionType | None:
    """将标题文本映射到 Section 类型；无法识别返回 None。"""
    normalized = title.strip().lower()
    if not normalized:
        return None
    for section_type, keywords in _SECTION_KEYWORDS:
        for kw in keywords:
            if kw in normalized:
                return section_type
    return None


def _to_block(item: Any) -> TextBlock:
    """将 TextBlock 或持久化的 dict（{type,text,page}）归一为 TextBlock。"""
    if isinstance(item, TextBlock):
        return item
    if isinstance(item, dict):
        return TextBlock(
            type=str(item.get("type", "paragraph")),
            text=str(item.get("text", "")),
            page=item.get("page"),
        )
    return TextBlock(text=str(item))


def split_sections(blocks: list[Any]) -> list[ResumeSection]:
    """按标题启发式将文本块切分为语义区块。

    - 遇到「可识别为 Section 标题」的 heading 块时开启新区块；
    - 首个已识别标题之前的内容归为 basic_info（若非空）；
    - 每个区块的 raw_text 为其内部块文本按空行拼接。
    """
    normalized = [_to_block(b) for b in blocks]

    sections: list[ResumeSection] = []
    # 首个标题前的内容缓冲，归入 basic_info
    preamble: list[TextBlock] = []
    current: ResumeSection | None = None

    for block in normalized:
        text = block.text.strip()
        if not text:
            continue

        # 标题候选：块被标注为 heading，或形似标题的短行
        is_heading = block.type == BLOCK_HEADING or is_heading_line(text)
        section_type = _match_section_type(text) if is_heading else None

        if section_type is not None:
            # 开启新区块
            current = ResumeSection(section_type=section_type, title=text, raw_text="", blocks=[])
            sections.append(current)
            continue

        if current is None:
            preamble.append(block)
        else:
            current.blocks.append(block)

    # 组装每个区块的 raw_text
    result: list[ResumeSection] = []
    if preamble:
        result.append(
            ResumeSection(
                section_type=ResumeSectionType.BASIC_INFO,
                title="basic_info",
                raw_text="\n\n".join(b.text.strip() for b in preamble),
                blocks=preamble,
            )
        )
    for section in sections:
        section.raw_text = "\n\n".join(b.text.strip() for b in section.blocks)
        result.append(section)

    return result
