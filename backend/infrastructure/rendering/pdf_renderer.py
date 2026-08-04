"""PDF 渲染器与确定性分页候选选择。"""

from __future__ import annotations

from dataclasses import dataclass

import pymupdf

from backend.domain.resume_builder.enums import LayoutDensity
from backend.domain.resume_builder.schemas import DENSITY_ORDER, LayoutPolicy, ResumeDraft
from backend.infrastructure.rendering.html_renderer import HtmlRenderer


@dataclass(frozen=True)
class LayoutCandidate:
    """一档排版密度对应的真实 PDF 结果。"""

    density: LayoutDensity
    pdf_bytes: bytes
    page_count: int


def count_pdf_pages(pdf_bytes: bytes) -> int:
    """从 PDF 页树读取真实页数。"""
    try:
        # pymupdf 未提供完整类型存根；与 pdf_parser 保持同一调用约定
        document = pymupdf.open(stream=pdf_bytes, filetype="pdf")  # type: ignore[no-untyped-call]
    except Exception as exc:
        raise ValueError("Invalid PDF") from exc
    try:
        page_count = int(document.page_count)
        if page_count < 1:
            raise ValueError("Invalid PDF: no pages")
        return page_count
    finally:
        document.close()  # type: ignore[no-untyped-call]


def select_layout_candidate(
    candidates: list[LayoutCandidate],
    policy: LayoutPolicy,
) -> tuple[LayoutCandidate, bool]:
    """按分页策略选择候选结果，候选顺序必须从松到紧。"""
    if not candidates:
        raise ValueError("At least one layout candidate is required")

    if policy.target_page_count is not None:
        for candidate in candidates:
            if candidate.page_count == policy.target_page_count:
                return candidate, True

    minimum_page_count = min(candidate.page_count for candidate in candidates)
    selected = next(candidate for candidate in candidates if candidate.page_count == minimum_page_count)
    return selected, policy.target_page_count is None


class PdfRenderer:
    """基于 Playwright 的确定性 A4 分页渲染器。"""

    def __init__(self, renderer: HtmlRenderer | None = None) -> None:
        self._renderer = renderer or HtmlRenderer()

    async def render_pdf(
        self,
        draft: ResumeDraft,
        layout_policy: LayoutPolicy | None = None,
        photo_data_uri: str | None = None,
    ) -> tuple[bytes, int, bool, LayoutDensity]:
        """渲染全部密度候选并返回策略选中的真实 PDF。"""
        from playwright.async_api import async_playwright

        policy = layout_policy or draft.layout_policy
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(args=["--no-sandbox"])
            try:
                page = await browser.new_page()
                await page.emulate_media(media="print")
                candidates: list[LayoutCandidate] = []
                for density in DENSITY_ORDER:
                    html = self._renderer.render(
                        draft,
                        density_override=density,
                        photo_data_uri=photo_data_uri,
                    )
                    await page.set_content(html, wait_until="networkidle")
                    await page.evaluate("document.fonts.ready")
                    pdf_bytes = await page.pdf(
                        format="A4",
                        print_background=True,
                        prefer_css_page_size=True,
                    )
                    candidates.append(
                        LayoutCandidate(
                            density=density,
                            pdf_bytes=pdf_bytes,
                            page_count=count_pdf_pages(pdf_bytes),
                        )
                    )

                selected, target_met = select_layout_candidate(candidates, policy)
                return (
                    selected.pdf_bytes,
                    selected.page_count,
                    target_met,
                    selected.density,
                )
            finally:
                await browser.close()
