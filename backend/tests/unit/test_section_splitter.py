"""Section 切分器单元测试 —— 覆盖标题识别与 8 类映射、basic_info 前导归集与回退。"""

from backend.domain.resume.enums import ResumeSectionType
from backend.infrastructure.extractors.section_splitter import (
    ResumeSection,
    _match_section_type,
    split_sections,
)
from backend.infrastructure.parsers.base import BLOCK_HEADING, BLOCK_PARAGRAPH, TextBlock


def test_match_section_type_covers_eight_categories() -> None:
    cases = {
        "基本信息": ResumeSectionType.BASIC_INFO,
        "教育背景": ResumeSectionType.EDUCATION,
        "工作经历": ResumeSectionType.WORK_EXPERIENCE,
        "项目经验": ResumeSectionType.PROJECT_EXPERIENCE,
        "专业技能": ResumeSectionType.SKILLS,
        "资格证书": ResumeSectionType.CERTIFICATES,
        "获奖经历": ResumeSectionType.AWARDS,
        "自我评价": ResumeSectionType.SELF_EVALUATION,
    }
    for title, expected in cases.items():
        assert _match_section_type(title) == expected


def test_match_section_type_english_and_case_insensitive() -> None:
    assert _match_section_type("EDUCATION") == ResumeSectionType.EDUCATION
    assert _match_section_type("Work Experience") == ResumeSectionType.WORK_EXPERIENCE
    assert _match_section_type("Self Evaluation") == ResumeSectionType.SELF_EVALUATION


def test_match_section_type_unknown_returns_none() -> None:
    assert _match_section_type("随便写点什么") is None
    assert _match_section_type("") is None


def test_split_sections_groups_content_under_headings() -> None:
    blocks = [
        TextBlock(type=BLOCK_HEADING, text="张三"),
        TextBlock(type=BLOCK_PARAGRAPH, text="电话：123456"),
        TextBlock(type=BLOCK_HEADING, text="工作经历"),
        TextBlock(type=BLOCK_PARAGRAPH, text="公司A：后端开发"),
        TextBlock(type=BLOCK_HEADING, text="项目经验"),
        TextBlock(type=BLOCK_PARAGRAPH, text="项目X：分布式系统"),
        TextBlock(type=BLOCK_HEADING, text="自我评价"),
        TextBlock(type=BLOCK_PARAGRAPH, text="乐于学习，抗压能力强。"),
    ]

    sections = split_sections(blocks)
    types = [s.section_type for s in sections]

    # 首个标题「张三」不可识别，前导内容归为 basic_info
    assert types[0] == ResumeSectionType.BASIC_INFO
    assert "张三" in sections[0].raw_text
    assert "电话：123456" in sections[0].raw_text

    assert ResumeSectionType.WORK_EXPERIENCE in types
    assert ResumeSectionType.PROJECT_EXPERIENCE in types
    assert ResumeSectionType.SELF_EVALUATION in types

    work = next(s for s in sections if s.section_type == ResumeSectionType.WORK_EXPERIENCE)
    assert "公司A：后端开发" in work.raw_text
    assert work.title == "工作经历"


def test_split_sections_accepts_persisted_dicts() -> None:
    blocks = [
        {"type": "heading", "text": "教育背景", "page": 1},
        {"type": "paragraph", "text": "某大学 计算机科学", "page": 1},
    ]

    sections = split_sections(blocks)

    assert len(sections) == 1
    assert sections[0].section_type == ResumeSectionType.EDUCATION
    assert "某大学 计算机科学" in sections[0].raw_text


def test_split_sections_empty_input() -> None:
    assert split_sections([]) == []


def test_resume_section_dataclass_defaults() -> None:
    section = ResumeSection(
        section_type=ResumeSectionType.SKILLS,
        title="技能",
        raw_text="Python",
    )
    assert section.blocks == []
