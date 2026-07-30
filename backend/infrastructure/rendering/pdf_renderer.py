"""PDF 渲染器 —— 用 Playwright(chromium) 把 HTML 打印为 A4 PDF，支持自动一页。

自动一页算法：A4 96dpi 单页可视高约 1123px；从当前密度档位起逐档收紧，
重新渲染并测量内容高度，选出首个不溢出的档位；仍溢出则返回 overflow=True。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.domain.resume_builder.enums import LayoutDensity
from backend.domain.resume_builder.schemas import DENSITY_ORDER, ResumeDraft
from backend.infrastructure.rendering.html_renderer import HtmlRenderer

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

# A4 在 96dpi 下的单页高度（297mm ≈ 1123px），留几像素容差抵消取整误差
A4_HEIGHT_PX = 1123.0
FIT_TOLERANCE_PX = 4.0


def select_fit_density(
    heights: dict[LayoutDensity, float],
    start_density: LayoutDensity,
    page_limit_px: float = A4_HEIGHT_PX + FIT_TOLERANCE_PX,
) -> tuple[LayoutDensity, bool]:
    """纯函数：从 start_density 起逐档收紧，选出首个高度不溢出的密度档位。

    Args:
        heights: 各密度档位对应的实测内容高度（px）。
        start_density: 起始（最松）档位，只会向更紧方向收缩。
        page_limit_px: 单页高度上限。

    Returns:
        (选中的密度, 是否仍溢出)。全部溢出时返回最紧档 + True。
    """
    start_idx = DENSITY_ORDER.index(start_density)
    for density in DENSITY_ORDER[start_idx:]:
        height = heights.get(density)
        if height is not None and height <= page_limit_px:
            return density, False
    return DENSITY_ORDER[-1], True


class PdfRenderer:
    """基于 Playwright 的 PDF 渲染器。"""

    def __init__(self, renderer: HtmlRenderer | None = None) -> None:
        self._renderer = renderer or HtmlRenderer()

    async def render_pdf(
        self,
        draft: ResumeDraft,
        auto_one_page: bool = False,
        photo_data_uri: str | None = None,
    ) -> tuple[bytes, int, bool]:
        """把草稿渲染为 PDF 字节。

        Args:
            draft: 简历草稿。
            auto_one_page: 是否启用自动一页收缩。
            photo_data_uri: 证件照 data URI（内联进 HTML，无外部网络请求）。

        Returns:
            (pdf_bytes, page_count, overflow)。overflow 仅在 auto_one_page 且
            收紧到最紧档后仍超过一页时为 True。
        """
        from playwright.async_api import async_playwright

        overflow = False
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(args=["--no-sandbox"])
            try:
                page = await browser.new_page()
                await page.emulate_media(media="print")

                if auto_one_page:
                    density, overflow = await self._fit_one_page(page, draft, photo_data_uri)
                    html = self._renderer.render(draft, density_override=density, photo_data_uri=photo_data_uri)
                else:
                    html = self._renderer.render(draft, photo_data_uri=photo_data_uri)

                await page.set_content(html, wait_until="networkidle")
                pdf_bytes = await page.pdf(format="A4", print_background=True)
                page_count = await self._count_pages(page)
                return pdf_bytes, page_count, overflow
            finally:
                await browser.close()

    async def _fit_one_page(
        self,
        page: Page,
        draft: ResumeDraft,
        photo_data_uri: str | None = None,
    ) -> tuple[LayoutDensity, bool]:
        """从草稿当前密度起逐档收紧，测量各档高度并选出适配一页的档位。"""
        start_density = draft.design_tokens.density
        start_idx = DENSITY_ORDER.index(start_density)
        heights: dict[LayoutDensity, float] = {}

        for density in DENSITY_ORDER[start_idx:]:
            html = self._renderer.render(draft, density_override=density, photo_data_uri=photo_data_uri)
            await page.set_content(html, wait_until="networkidle")
            height = await page.evaluate("document.body.scrollHeight")
            heights[density] = float(height)
            # 命中即可提前停止，无需继续收紧
            if heights[density] <= A4_HEIGHT_PX + FIT_TOLERANCE_PX:
                break

        return select_fit_density(heights, start_density)

    async def _count_pages(self, page: Page) -> int:
        """估算 PDF 页数：内容总高 / 单页高度，向上取整，至少 1 页。"""
        total = await page.evaluate("document.body.scrollHeight")
        pages = int((float(total) + A4_HEIGHT_PX - 1) // A4_HEIGHT_PX)
        return max(1, pages)
