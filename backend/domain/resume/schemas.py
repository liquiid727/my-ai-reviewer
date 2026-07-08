from pydantic import BaseModel,Field
from typing import List, Optional, Any, Dict
from datetime import date

# resume 数据建模
class Evidence(BaseModel):
    source_text: str
    page:Optional[int] = None
    section:Optional[str] = None
    confidence:float = Field(default=0.0,ge=0,le=1)
# 定义用户联系信息
class Identity(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    links: List[str] = []
# 教育背景
# 这里要增设为本科+研究生+博士+其他的内容，允许有多个教育背景
class Education(BaseModel):
    school: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    evidence: Optional[Evidence] = None

# 工作经历
class WorkExperience(BaseModel):
    company:Optional[str] = None
    title:Optional[str]=None
    start_date:Optional[str]=None
    end_date:Optional[str]=None
    responsibilities:List[str]= []
    achievements:List[str]=[]
    evidence:Optional[Evidence]= None

# 项目经历
class ProjectExperience(BaseModel):
    name:Optional[str] = None
    role:Optional[str] = None
    tech_stack:List[str] = []
    background:Optional[str] = None
    responsibilitity:Optional[str]=None
    highlights:List[str] = []
    metrics: List[str]= []
    evidence:Optional[Evidence]=None

class Skill(BaseModel):
    name:str
    category:Optional[str] = None
    evidence:Optional[str] =None
    confidence:float = Field(default=0.0,ge=0,le=1)


class Certificate(BaseModel):
    name:str
    issuer: Optional[str] = None
    issued_at: Optional[str] = None
    evidence: Optional[Evidence] = None


class CandidateProfile(BaseModel):
    identity:Identity =Identity()
    education:List[Education] = []
    work_experiences: List[WorkExperience] = []
    projects: List[ProjectExperience] = []
    skills: List[Skill] = []
    certificates: List[Certificate] = []
    ability_tags: List[str] = []
    interview_clues: List[str] = []
    risks: List[str] = []


# 核心建模
class ResumeFact(BaseModel):
    fact_type:str
    key:str
    value:Any
    evidence:Evidence
    metadata:Dict[str,Any] = {}


class DimensionScore(BaseModel):
    dimension: str
    score: float = Field(ge=0, le=100)
    comment: Optional[str] = None


class ResumeEvaluation(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    dimension_scores: List[DimensionScore] = []
    strengths: List[str] = []
    risks: List[str] = []
    interview_suggestions: List[str] = []
    summary: Optional[str] = None
    llm_model: Optional[str] = None
