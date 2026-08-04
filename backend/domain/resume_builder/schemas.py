"""简历制作领域数据模型 —— 草稿、设计令牌、润色与导出的 Pydantic 模型。"""

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from backend.domain.resume.enums import ResumeSectionType
from backend.domain.resume_builder.enums import LayoutDensity, LayoutMode, TemplateId

# 密度档位从松到紧的固定顺序（自动分页按此顺序比较候选方案）
DENSITY_ORDER: list[LayoutDensity] = [
    LayoutDensity.LOOSE,
    LayoutDensity.NORMAL,
    LayoutDensity.TIGHT,
    LayoutDensity.COMPACT,
]

# 每个密度档位对应的排版参数（渲染时注入为 CSS 变量）
_DENSITY_PARAMS: dict[LayoutDensity, dict[str, str]] = {
    LayoutDensity.LOOSE: {"font_scale": "1.06", "line_height": "1.6", "section_gap": "18px"},
    LayoutDensity.NORMAL: {"font_scale": "1.0", "line_height": "1.45", "section_gap": "14px"},
    LayoutDensity.TIGHT: {"font_scale": "0.94", "line_height": "1.3", "section_gap": "10px"},
    LayoutDensity.COMPACT: {"font_scale": "0.88", "line_height": "1.2", "section_gap": "7px"},
}


def density_params(density: LayoutDensity) -> dict[str, str]:
    """返回某密度档位的排版参数（font_scale / line_height / section_gap）。"""
    return _DENSITY_PARAMS[density]


class DesignTokens(BaseModel):
    """简历的视觉设计令牌 —— 控制模板的字体、密度、主色与页边距。"""
    font_family: str = "'Noto Sans SC', 'Helvetica Neue', Arial, sans-serif"
    density: LayoutDensity = LayoutDensity.NORMAL
    accent_color: str = "#2563eb"       # 主题色（标题/分隔线）
    page_margin: str = "48px"           # 页面内边距
    custom_css: str = ""                # 用户自定义 CSS（注入模板末尾，可覆盖默认样式）


class LayoutPolicy(BaseModel):
    """自动分页策略；目标页数模式必须显式提供页数。"""

    mode: LayoutMode = LayoutMode.AUTO_PAGES
    target_page_count: int | None = Field(default=None, ge=1, le=10)

    @model_validator(mode="after")
    def validate_target_page_count(self) -> "LayoutPolicy":
        if self.mode == LayoutMode.TARGET_PAGES and self.target_page_count is None:
            raise ValueError("target_page_count is required for target_pages")
        if self.mode == LayoutMode.AUTO_PAGES and self.target_page_count is not None:
            raise ValueError("target_page_count is only valid for target_pages")
        return self


class DraftItem(BaseModel):
    """草稿中的一个可编辑条目（如一段经历、一个项目、一个技能组）。"""
    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    heading: Optional[str] = None       # 条目标题（公司/项目/学校名等）
    subheading: Optional[str] = None    # 副标题（职位/角色/学位等）
    date_range: Optional[str] = None    # 时间范围
    bullets: List[str] = []             # 要点列表（AI 润色的作用对象）


class DraftSection(BaseModel):
    """草稿中的一个区块。"""
    section_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    section_type: ResumeSectionType
    title: str                          # 区块标题（可自定义，如「工作经历」）
    items: List[DraftItem] = []         # 结构化条目
    visible: bool = True                # 是否在导出中显示
    order: int = 0                      # 排序序号


class ResumeDraft(BaseModel):
    """一份可编辑的简历草稿。"""
    title: str = "我的简历"
    identity: Dict[str, Any] = Field(default_factory=dict)  # 姓名/邮箱/电话/城市/链接
    summary: Optional[str] = None                 # 个人简介 / 自我评价
    sections: List[DraftSection] = []
    template_id: TemplateId = TemplateId.CLASSIC
    design_tokens: DesignTokens = Field(default_factory=DesignTokens)
    layout_policy: LayoutPolicy = Field(default_factory=LayoutPolicy)


class PolishRequest(BaseModel):
    """AI 润色请求 —— 针对某区块的一组要点。"""
    section_type: ResumeSectionType
    items: List[str]                    # 待润色的原始要点
    context: Optional[str] = None       # 补充上下文（如目标岗位）


class PolishResult(BaseModel):
    """AI 润色结果 —— 保留原文，给出润色建议供逐条接受。"""
    original_items: List[str]
    polished_items: List[str]
    notes: Optional[str] = None


class ExportOptions(BaseModel):
    """导出 PDF 的选项。"""
    template_id: Optional[TemplateId] = None   # 覆盖草稿模板（可选）
    layout_policy: LayoutPolicy | None = None  # 覆盖草稿分页策略（可选）
    persist: bool = False                      # 是否将 PDF 存入对象存储并记录
    replacements: dict[str, str] = Field(default_factory=dict)


class ExportResult(BaseModel):
    """导出结果元信息。"""
    page_count: int
    target_met: bool = True
    applied_density: LayoutDensity = LayoutDensity.NORMAL
    storage_path: Optional[str] = None  # 若持久化，返回 MinIO 对象名
