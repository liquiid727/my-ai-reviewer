"""HTML 渲染器 —— 用 Jinja2 把简历草稿渲染为 HTML，注入设计令牌为 CSS 变量。

预览（iframe）与导出（Playwright 打印）复用同一份 HTML，保证像素级一致。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.domain.resume_builder.enums import LayoutDensity, TemplateId
from backend.domain.resume_builder.schemas import (
    DesignTokens,
    ResumeDraft,
    density_params,
)

# 模板目录
_TEMPLATES_DIR = Path(__file__).parent / "templates"

# 模板 id → 模板文件名
_TEMPLATE_FILES: dict[TemplateId, str] = {
    TemplateId.CLASSIC: "classic.html",
    TemplateId.MODERN: "modern.html",
    TemplateId.COMPACT: "compact.html",
}


class HtmlRenderer:
    """基于 Jinja2 的简历 HTML 渲染器（autoescape 开启，防 XSS）。"""

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(
        self,
        draft: ResumeDraft,
        density_override: LayoutDensity | None = None,
    ) -> str:
        """把草稿渲染为完整 HTML 字符串。

        Args:
            draft: 简历草稿。
            density_override: 覆盖草稿密度（自动一页收缩时使用）。
        """
        tokens = draft.design_tokens
        density = density_override or tokens.density
        css_vars = _build_css_vars(tokens, density)

        template_file = _TEMPLATE_FILES.get(draft.template_id, "classic.html")
        template = self._env.get_template(template_file)

        # 仅渲染可见区块，并按 order 排序
        sections = sorted(
            [s for s in draft.sections if s.visible],
            key=lambda s: s.order,
        )

        return template.render(
            draft=draft,
            identity=draft.identity,
            summary=draft.summary,
            sections=sections,
            css_vars=css_vars,
        )


def _build_css_vars(tokens: DesignTokens, density: LayoutDensity) -> dict[str, Any]:
    """把设计令牌 + 密度参数合成为模板使用的 CSS 变量字典。"""
    params = density_params(density)
    return {
        "font_family": tokens.font_family,
        "accent_color": tokens.accent_color,
        "page_margin": tokens.page_margin,
        "font_scale": params["font_scale"],
        "line_height": params["line_height"],
        "section_gap": params["section_gap"],
    }
