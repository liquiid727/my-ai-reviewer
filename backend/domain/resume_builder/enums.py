"""简历制作领域枚举 —— 模板与排版密度。"""

from enum import Enum


class TemplateId(str, Enum):
    """内置简历模板。"""
    CLASSIC = "classic"    # 经典单栏
    MODERN = "modern"      # 现代双栏（左侧栏 + 主栏）
    COMPACT = "compact"    # 紧凑（信息密度高，适合内容多的简历）


class LayoutDensity(str, Enum):
    """排版密度档位 —— 自动一页时从松到紧逐档收缩。"""
    LOOSE = "loose"        # 宽松
    NORMAL = "normal"      # 正常
    TIGHT = "tight"        # 紧凑
    COMPACT = "compact"    # 极紧
