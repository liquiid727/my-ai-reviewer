"""自动一页密度选择逻辑的单元测试（纯函数，免浏览器）。"""

from backend.domain.resume_builder.enums import LayoutDensity
from backend.infrastructure.rendering.pdf_renderer import (
    A4_HEIGHT_PX,
    select_fit_density,
)


def test_start_density_fits_immediately() -> None:
    heights = {LayoutDensity.NORMAL: 1000.0}
    density, overflow = select_fit_density(heights, LayoutDensity.NORMAL)
    assert density == LayoutDensity.NORMAL
    assert overflow is False


def test_shrinks_to_first_fitting_density() -> None:
    heights = {
        LayoutDensity.NORMAL: 1300.0,   # 溢出
        LayoutDensity.TIGHT: 1100.0,    # 适配
        LayoutDensity.COMPACT: 900.0,
    }
    density, overflow = select_fit_density(heights, LayoutDensity.NORMAL)
    assert density == LayoutDensity.TIGHT
    assert overflow is False


def test_all_overflow_returns_tightest_with_flag() -> None:
    heights = {
        LayoutDensity.NORMAL: 2000.0,
        LayoutDensity.TIGHT: 1800.0,
        LayoutDensity.COMPACT: 1500.0,
    }
    density, overflow = select_fit_density(heights, LayoutDensity.NORMAL)
    assert density == LayoutDensity.COMPACT
    assert overflow is True


def test_only_shrinks_never_loosens() -> None:
    # 起始档为 TIGHT，即便 LOOSE/NORMAL 也测过，也不会往更松方向选
    heights = {
        LayoutDensity.LOOSE: 900.0,
        LayoutDensity.NORMAL: 900.0,
        LayoutDensity.TIGHT: 1100.0,
    }
    density, overflow = select_fit_density(heights, LayoutDensity.TIGHT)
    assert density == LayoutDensity.TIGHT
    assert overflow is False


def test_tolerance_boundary_fits() -> None:
    # 恰好等于单页高度上限（含容差）应视为适配
    heights = {LayoutDensity.NORMAL: A4_HEIGHT_PX}
    density, overflow = select_fit_density(heights, LayoutDensity.NORMAL)
    assert density == LayoutDensity.NORMAL
    assert overflow is False
