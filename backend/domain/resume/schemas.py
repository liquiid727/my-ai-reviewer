"""简历领域数据模型 —— 定义简历结构化信息的 Pydantic 模型。"""

from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from backend.domain.resume.enums import SkillCategory

# 自由文本分类 → SkillCategory 枚举的归一映射（小写、去空格后匹配）
_SKILL_CATEGORY_ALIASES: dict[str, SkillCategory] = {
    "language": SkillCategory.PROGRAMMING_LANGUAGE,
    "languages": SkillCategory.PROGRAMMING_LANGUAGE,
    "programminglanguage": SkillCategory.PROGRAMMING_LANGUAGE,
    "programming": SkillCategory.PROGRAMMING_LANGUAGE,
    "编程语言": SkillCategory.PROGRAMMING_LANGUAGE,
    "语言": SkillCategory.PROGRAMMING_LANGUAGE,
    "framework": SkillCategory.FRAMEWORK,
    "frameworks": SkillCategory.FRAMEWORK,
    "library": SkillCategory.FRAMEWORK,
    "框架": SkillCategory.FRAMEWORK,
    "database": SkillCategory.DATABASE,
    "db": SkillCategory.DATABASE,
    "数据库": SkillCategory.DATABASE,
    "cache": SkillCategory.CACHE,
    "caching": SkillCategory.CACHE,
    "缓存": SkillCategory.CACHE,
    "mq": SkillCategory.MQ,
    "messagequeue": SkillCategory.MQ,
    "messaging": SkillCategory.MQ,
    "消息队列": SkillCategory.MQ,
    "cloudnative": SkillCategory.CLOUD_NATIVE,
    "cloud": SkillCategory.CLOUD_NATIVE,
    "云原生": SkillCategory.CLOUD_NATIVE,
    "ai": SkillCategory.AI,
    "ml": SkillCategory.AI,
    "machinelearning": SkillCategory.AI,
    "llm": SkillCategory.AI,
    "devops": SkillCategory.DEVOPS,
    "ops": SkillCategory.DEVOPS,
    "cicd": SkillCategory.DEVOPS,
    "testing": SkillCategory.TESTING,
    "test": SkillCategory.TESTING,
    "qa": SkillCategory.TESTING,
    "测试": SkillCategory.TESTING,
    "architecture": SkillCategory.ARCHITECTURE,
    "architect": SkillCategory.ARCHITECTURE,
    "架构": SkillCategory.ARCHITECTURE,
}


def _normalize_skill_category(value: Optional[str]) -> Optional[str]:
    """将自由文本的技能分类归一到 SkillCategory；无法识别时归到 other。"""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    key = raw.lower().replace(" ", "").replace("-", "").replace("_", "")
    # 已是合法枚举值
    for member in SkillCategory:
        if key == member.value.replace("_", ""):
            return member.value
    mapped = _SKILL_CATEGORY_ALIASES.get(key)
    return (mapped or SkillCategory.OTHER).value


class Evidence(BaseModel):
    """事实证据：记录信息来源的原文、位置和置信度。"""
    source_text: str               # 原文摘录
    page:Optional[int] = None      # 所在页码
    section:Optional[str] = None   # 所在区块
    confidence:float = Field(default=0.0,ge=0,le=1)  # 置信度 (0~1)


class Identity(BaseModel):
    """候选人基本身份信息。"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None  # 所在城市/地区
    links: List[str] = []           # 个人链接（GitHub、LinkedIn 等）


class Education(BaseModel):
    """教育背景（支持多条：本科、硕士、博士等）。"""
    school: Optional[str] = None
    degree: Optional[str] = None     # 学位（学士/硕士/博士）
    major: Optional[str] = None      # 专业
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str] = None        # 绩点（可选）
    evidence: Optional[Evidence] = None


class WorkExperience(BaseModel):
    """工作经历。"""
    company:Optional[str] = None
    title:Optional[str]=None           # 职位
    start_date:Optional[str]=None
    end_date:Optional[str]=None
    responsibilities:List[str]= []     # 工作职责
    achievements:List[str]=[]          # 工作成果
    tech_stack:List[str] = []          # 该经历涉及的技术栈
    industry:Optional[str] = None      # 所属行业
    evidence:Optional[Evidence]= None


class ProjectExperience(BaseModel):
    """项目经历。"""
    # 兼容旧数据里的拼写错误字段名 responsibilitity
    model_config = ConfigDict(populate_by_name=True)

    name:Optional[str] = None          # 项目名称
    role:Optional[str] = None          # 担任角色
    tech_stack:List[str] = []          # 技术栈
    background:Optional[str] = None    # 项目背景
    responsibility:Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("responsibility", "responsibilitity"),
    )                                  # 负责内容（兼容旧字段 responsibilitity）
    difficulties:List[str] = []        # 项目难点
    team_size:Optional[str] = None     # 团队规模
    highlights:List[str] = []          # 项目亮点
    metrics: List[str]= []            # 量化指标
    evidence:Optional[Evidence]=None


class Skill(BaseModel):
    """技能信息。"""
    name:str                           # 技能名称
    category:Optional[str] = None      # 分类（见 SkillCategory，非法值归一到 other）
    evidence:Optional[str] =None       # 技能证据
    confidence:float = Field(default=0.0,ge=0,le=1)  # 置信度

    @field_validator("category", mode="before")
    @classmethod
    def _coerce_category(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_skill_category(v)


class Certificate(BaseModel):
    """证书信息。"""
    name:str                           # 证书名称
    issuer: Optional[str] = None       # 颁发机构
    issued_at: Optional[str] = None    # 获得时间
    evidence: Optional[Evidence] = None


class CandidateProfile(BaseModel):
    """候选人完整画像 —— 聚合所有结构化信息。"""
    identity:Identity =Identity()
    education:List[Education] = []
    work_experiences: List[WorkExperience] = []
    projects: List[ProjectExperience] = []
    skills: List[Skill] = []
    certificates: List[Certificate] = []
    ability_tags: List[str] = []       # 能力标签（由分类器生成）
    interview_clues: List[str] = []    # 面试线索（建议追问的方向）
    risks: List[str] = []             # 风险点（经历空白、信息模糊等）


class ResumeFact(BaseModel):
    """核心事实建模 —— 从简历中提取的单条结构化事实。"""
    fact_type:str           # 事实类型（见 FactType 枚举）
    key:str                 # 标识键（如公司名、学校名）
    value:Any               # 结构化的值
    evidence:Evidence       # 原文证据
    metadata:Dict[str,Any] = {}  # 附加元数据


class DimensionScore(BaseModel):
    """评估维度评分。"""
    dimension: str                     # 维度名称
    score: float = Field(ge=0, le=100)  # 分数 (0~100)
    comment: Optional[str] = None      # 评语 / 理由
    evidence: Optional[str] = None     # 支撑证据（简历原文片段）


class ResumeEvaluation(BaseModel):
    """简历综合评估结果。"""
    overall_score: float = Field(ge=0, le=100)  # 综合评分
    dimension_scores: List[DimensionScore] = []  # 各维度评分
    strengths: List[str] = []           # 优势
    risks: List[str] = []              # 风险
    interview_suggestions: List[str] = []  # 面试建议
    summary: Optional[str] = None       # 总结评语
    llm_model: Optional[str] = None     # 使用的模型
