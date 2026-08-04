"""HTML 渲染器的单元测试 —— 关键字段、CSS 变量注入、autoescape。"""

from backend.domain.resume.enums import ResumeSectionType
from backend.domain.resume_builder.enums import LayoutDensity, TemplateId
from backend.domain.resume_builder.schemas import (
    DesignTokens,
    DraftItem,
    DraftSection,
    ResumeDraft,
    density_params,
)
from backend.infrastructure.rendering.html_renderer import HtmlRenderer


def _sample_draft(**kwargs: object) -> ResumeDraft:
    return ResumeDraft(
        title="张三的简历",
        identity={"name": "张三", "email": "z@example.com", "phone": "13800000000"},
        summary="资深后端工程师",
        sections=[
            DraftSection(
                section_type=ResumeSectionType.WORK_EXPERIENCE,
                title="工作经历",
                items=[
                    DraftItem(
                        heading="字节跳动",
                        subheading="后端工程师",
                        date_range="2020 ~ 2023",
                        bullets=["主导订单系统重构"],
                    )
                ],
                order=1,
            ),
        ],
        **kwargs,  # type: ignore[arg-type]
    )


def test_render_contains_key_fields() -> None:
    html = HtmlRenderer().render(_sample_draft())
    assert "张三" in html
    assert "z@example.com" in html
    assert "工作经历" in html
    assert "字节跳动" in html
    assert "主导订单系统重构" in html
    assert "<!DOCTYPE html>" in html


def test_design_tokens_injected_as_css_vars() -> None:
    draft = _sample_draft(
        design_tokens=DesignTokens(
            density=LayoutDensity.TIGHT,
            accent_color="#123456",
        )
    )
    html = HtmlRenderer().render(draft)
    params = density_params(LayoutDensity.TIGHT)

    assert "--accent: #123456;" in html
    assert f"--font-scale: {params['font_scale']};" in html
    assert f"--section-gap: {params['section_gap']};" in html


def test_print_layout_repeats_page_margin_and_protects_content_blocks() -> None:
    html = HtmlRenderer().render(_sample_draft())

    assert "@page" in html
    assert "margin: 48px;" in html
    assert ".item {" in html
    assert "break-inside: avoid;" in html
    assert "break-after: avoid;" in html


def test_density_override_takes_precedence() -> None:
    draft = _sample_draft(design_tokens=DesignTokens(density=LayoutDensity.LOOSE))
    html = HtmlRenderer().render(draft, density_override=LayoutDensity.COMPACT)
    compact = density_params(LayoutDensity.COMPACT)
    assert f"--font-scale: {compact['font_scale']};" in html


def test_autoescape_prevents_injection() -> None:
    draft = _sample_draft()
    draft.identity = {"name": "<script>alert(1)</script>"}
    html = HtmlRenderer().render(draft)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_hidden_section_not_rendered() -> None:
    draft = _sample_draft()
    draft.sections.append(
        DraftSection(
            section_type=ResumeSectionType.SKILLS,
            title="隐藏技能区",
            items=[DraftItem(bullets=["机密"])],
            visible=False,
            order=2,
        )
    )
    html = HtmlRenderer().render(draft)
    assert "隐藏技能区" not in html
    assert "机密" not in html


def test_all_templates_render() -> None:
    for template_id in TemplateId:
        draft = _sample_draft(template_id=template_id)
        html = HtmlRenderer().render(draft)
        assert "张三" in html


# ─────────────────────────── 证件照区块（#034） ───────────────────────────

_PHOTO_URI = "data:image/png;base64,dGVzdA=="


def test_photo_rendered_in_all_templates() -> None:
    """三套模板均渲染头像区块，data URI 内联进 img src。"""
    for template_id in TemplateId:
        draft = _sample_draft(template_id=template_id)
        html = HtmlRenderer().render(draft, photo_data_uri=_PHOTO_URI)
        assert '<div class="photo-block">' in html
        assert '<img class="id-photo"' in html
        assert f'src="{_PHOTO_URI}"' in html


def test_no_photo_renders_without_photo_block() -> None:
    """无照片时三套模板均不产生头像标记（布局回归）。"""
    for template_id in TemplateId:
        draft = _sample_draft(template_id=template_id)
        html = HtmlRenderer().render(draft)
        assert '<div class="photo-block">' not in html
        assert "<img" not in html
        assert ' with-photo"' not in html


def test_no_photo_output_identical_to_explicit_none() -> None:
    """缺省参数与显式 None 渲染结果字符级一致。"""
    for template_id in TemplateId:
        draft = _sample_draft(template_id=template_id)
        assert HtmlRenderer().render(draft) == HtmlRenderer().render(draft, photo_data_uri=None)


def test_photo_with_density_override() -> None:
    """密度收缩时照片仍内联（自动一页链路用）。"""
    draft = _sample_draft(design_tokens=DesignTokens(density=LayoutDensity.LOOSE))
    html = HtmlRenderer().render(
        draft,
        density_override=LayoutDensity.COMPACT,
        photo_data_uri=_PHOTO_URI,
    )
    compact = density_params(LayoutDensity.COMPACT)
    assert f"--font-scale: {compact['font_scale']};" in html
    assert f'src="{_PHOTO_URI}"' in html
