"""简历制作领域枚举 —— 模板、排版密度与分页模式。"""

from enum import Enum


class TemplateId(str, Enum):
    """内置简历模板。"""

    CLASSIC = "classic"  # 经典单栏
    MODERN = "modern"  # 现代双栏（左侧栏 + 主栏）
    COMPACT = "compact"  # 紧凑（信息密度高，适合内容多的简历）


class LayoutDensity(str, Enum):
    """排版密度档位 —— 自动分页时用于受限的版式搜索。"""

    LOOSE = "loose"  # 宽松
    NORMAL = "normal"  # 正常
    TIGHT = "tight"  # 紧凑
    COMPACT = "compact"  # 极紧


class LayoutMode(str, Enum):
    """简历分页策略。"""

    AUTO_PAGES = "auto_pages"
    TARGET_PAGES = "target_pages"
