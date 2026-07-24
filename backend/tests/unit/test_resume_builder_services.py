"""简历制作领域服务的单元测试（免数据库的纯逻辑部分）。"""

from backend.domain.resume.enums import ResumeSectionType
from backend.domain.resume_builder.enums import TemplateId
from backend.domain.resume_builder.schemas import DesignTokens, ResumeDraft
from backend.domain.resume_builder.services import (
    _draft_content,
    draft_model_to_schema,
    draft_to_parsed_result,
    profile_to_draft,
)


class _FakeProfile:
    """模拟 CandidateProfileModel 的最小对象（免数据库）。"""

    def __init__(self, **kwargs: object) -> None:
        self.identity = kwargs.get("identity", {})
        self.education = kwargs.get("education", [])
        self.work_experiences = kwargs.get("work_experiences", [])
        self.projects = kwargs.get("projects", [])
        self.skills = kwargs.get("skills", [])
        self.certificates = kwargs.get("certificates", [])
        self.ability_tags = kwargs.get("ability_tags", [])
        self.interview_clues = kwargs.get("interview_clues", [])
        self.risks = kwargs.get("risks", [])


class _FakeDraftModel:
    """模拟 ResumeDraftModel 的最小对象（免数据库）。"""

    def __init__(self, content: dict, template_id: str, design_tokens: dict, title: str) -> None:
        self.content = content
        self.template_id = template_id
        self.design_tokens = design_tokens
        self.title = title


def test_profile_to_draft_maps_sections() -> None:
    profile = _FakeProfile(
        identity={"name": "张三", "email": "z@example.com"},
        work_experiences=[{
            "company": "字节跳动", "title": "后端工程师",
            "start_date": "2020", "end_date": "2023",
            "responsibilities": ["负责订单系统"], "achievements": ["QPS 提升 3 倍"],
        }],
        projects=[{"name": "支付网关", "role": "负责人", "highlights": ["高可用"]}],
        education=[{"school": "清华", "degree": "硕士", "major": "计算机", "gpa": "3.9"}],
        skills=[{"name": "Python", "category": "programming_language"}],
        certificates=[{"name": "PMP", "issuer": "PMI"}],
        ability_tags=["高并发", "分布式"],
    )
    draft = profile_to_draft(profile)  # type: ignore[arg-type]

    assert draft.title == "张三"
    assert draft.identity["email"] == "z@example.com"
    assert draft.summary == "高并发、分布式"
    assert draft.template_id == TemplateId.CLASSIC

    types = {s.section_type for s in draft.sections}
    assert ResumeSectionType.WORK_EXPERIENCE in types
    assert ResumeSectionType.PROJECT_EXPERIENCE in types
    assert ResumeSectionType.EDUCATION in types
    assert ResumeSectionType.SKILLS in types
    assert ResumeSectionType.CERTIFICATES in types

    work = next(s for s in draft.sections if s.section_type == ResumeSectionType.WORK_EXPERIENCE)
    assert work.items[0].heading == "字节跳动"
    assert work.items[0].date_range == "2020 ~ 2023"
    # responsibilities + achievements 合并为 bullets
    assert "负责订单系统" in work.items[0].bullets
    assert "QPS 提升 3 倍" in work.items[0].bullets


def test_profile_to_draft_empty_profile() -> None:
    draft = profile_to_draft(_FakeProfile())  # type: ignore[arg-type]
    assert draft.title == "我的简历"
    assert draft.sections == []
    assert draft.summary is None


def test_draft_content_roundtrip() -> None:
    original = ResumeDraft(
        title="我的简历",
        identity={"name": "李四"},
        summary="资深工程师",
        sections=[],
        template_id=TemplateId.MODERN,
        design_tokens=DesignTokens(accent_color="#ff0000"),
    )
    model = _FakeDraftModel(
        content=_draft_content(original),
        template_id="modern",
        design_tokens=original.design_tokens.model_dump(mode="json"),
        title="我的简历",
    )
    restored = draft_model_to_schema(model)  # type: ignore[arg-type]

    assert restored.identity == {"name": "李四"}
    assert restored.summary == "资深工程师"
    assert restored.template_id == TemplateId.MODERN
    assert restored.design_tokens.accent_color == "#ff0000"


def test_draft_to_parsed_result_shape() -> None:
    draft = ResumeDraft(title="t", identity={"name": "王五"}, summary="s", sections=[])
    parsed = draft_to_parsed_result(draft)
    assert parsed["identity"] == {"name": "王五"}
    assert parsed["summary"] == "s"
    assert parsed["sections"] == []
