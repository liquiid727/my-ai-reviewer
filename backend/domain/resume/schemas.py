"""简历领域数据模型 —— 定义简历结构化信息的 Pydantic 模型。"""

from pydantic import BaseModel,Field
from typing import List, Optional, Any, Dict
from datetime import date


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
    evidence: Optional[Evidence] = None


class WorkExperience(BaseModel):
    """工作经历。"""
    company:Optional[str] = None
    title:Optional[str]=None           # 职位
    start_date:Optional[str]=None
    end_date:Optional[str]=None
    responsibilities:List[str]= []     # 工作职责
    achievements:List[str]=[]          # 工作成果
    evidence:Optional[Evidence]= None


class ProjectExperience(BaseModel):
    """项目经历。"""
    name:Optional[str] = None          # 项目名称
    role:Optional[str] = None          # 担任角色
    tech_stack:List[str] = []          # 技术栈
    background:Optional[str] = None    # 项目背景
    responsibilitity:Optional[str]=None  # 负责内容
    highlights:List[str] = []          # 项目亮点
    metrics: List[str]= []            # 量化指标
    evidence:Optional[Evidence]=None


class Skill(BaseModel):
    """技能信息。"""
    name:str                           # 技能名称
    category:Optional[str] = None      # 分类（编程语言/框架/工具等）
    evidence:Optional[str] =None       # 技能证据
    confidence:float = Field(default=0.0,ge=0,le=1)  # 置信度


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
    comment: Optional[str] = None      # 评语


class ResumeEvaluation(BaseModel):
    """简历综合评估结果。"""
    overall_score: float = Field(ge=0, le=100)  # 综合评分
    dimension_scores: List[DimensionScore] = []  # 各维度评分
    strengths: List[str] = []           # 优势
    risks: List[str] = []              # 风险
    interview_suggestions: List[str] = []  # 面试建议
    summary: Optional[str] = None       # 总结评语
    llm_model: Optional[str] = None     # 使用的模型
