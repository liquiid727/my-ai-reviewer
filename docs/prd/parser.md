Resume Intelligence Platform（简历智能分析平台）
一、项目背景（Background）

目前简历解析大多停留在"提取 JSON"阶段，缺乏统一的数据模型、事实追溯能力以及 AI 后续分析能力。

对于招聘系统而言，一份简历不仅是一份文档，更是一份候选人的职业画像。

因此，本项目目标不是实现一个 Resume Parser，而是建设一套完整的 Resume Intelligence Platform，为后续 JD 匹配、面试 Agent、能力评估、人才画像等 AI 能力提供统一的数据底座。

二、项目目标（Goals）

建设一套完整的 Resume Domain，支持：

多格式简历解析
统一 Resume Domain 建模
可追溯 Fact 提取
Candidate Profile 标准化
AI Resume Evaluation
Interview Agent 数据输入
JD Matching 数据输入
后续 Talent Graph 数据沉淀

最终形成：

Resume

↓

Document

↓

ParsedText

↓

Section

↓

Facts

↓

Profile

↓

Evaluation

↓

Interview

↓

Matching

而不是：

PDF

↓

JSON
三、核心能力（Core Capabilities）
3.1 Resume Domain 建模

建立统一 Resume 聚合模型。

包括：

Resume

管理一份简历生命周期。

包括：

上传
解析
分类
评估
版本管理
状态管理
ResumeDocument

负责管理原始文件。

支持：

PDF
DOC
DOCX
HTML
Markdown
TXT

记录：

hash
parser version
文件来源
OCR状态
页数
ResumeParsedText

负责保存解析后的文本。

支持：

Raw Text
Paragraph
Heading
Block
Page

保证 Parser 可升级。

ResumeSection

自动识别：

Basic Information
Education
Work Experience
Projects
Skills
Certificates
Awards
Self Evaluation

作为后续 Retrieval 单位。

ResumeFact

抽取所有事实。

例如：

Skill

Project

Education

Work

Certificate

每个 Fact 保存：

Evidence
Confidence
Source Text
Page
Section
Parser Version

保证 AI 可解释。

CandidateProfile

根据 Facts 构建标准画像。

包括：

Identity

Education

Work

Projects

Skills

Ability Tags

Years

Industry

Architecture Experience

AI Experience

Cloud Experience

Leadership

等等。

四、简历解析（Resume Parsing）

支持：

文件类型

支持：

PDF
DOC
DOCX
HTML
Markdown
TXT

后续支持：

图片（OCR）
LinkedIn 导出
Boss 导出
拉勾导出
Parser Pipeline

统一流程：

Upload

↓

Detect File Type

↓

Document Parser

↓

Parsed Text

↓

Section Split

↓

Fact Extractor

↓

Profile Builder

↓

Classification

↓

Evaluation

Parser 应支持：

Parser Version

方便重新解析。

五、AI 信息抽取（Resume Extraction）

利用 LLM 对简历进行结构化抽取。

包括：

基础信息

姓名

联系方式

邮箱

城市

GitHub

博客

LinkedIn

教育背景

学校

学历

专业

毕业时间

GPA（可选）

工作经历

公司

职位

时间

职责

成果

技术栈

行业

项目经历

项目名称

背景

职责

技术

难点

亮点

业务指标

团队规模

角色

技能

Programming Language

Framework

Database

Cache

MQ

Cloud Native

AI

DevOps

Testing

Architecture

Fact Evidence

所有抽取结果必须保存：

Evidence

Confidence

Source

Page

Section

禁止仅输出最终 JSON。

六、Resume Classification

根据 Facts 自动生成标签。

例如：

Backend

Frontend

AI Engineer

LLM Engineer

Architect

DevOps

Game

Finance

E-commerce

Cloud Native

Distributed System

等等。

同时统计：

工作年限

项目数量

技术深度

行业覆盖

管理经验

七、AI Resume Evaluation

新增 Resume Evaluation Agent。

目标不是"打一个分"。

而是模拟真实技术面试官。

输出：

综合评分

例如：

Overall

85/100

各维度评分

技术能力

项目质量

工程能力

架构能力

业务复杂度

影响力

成长性

AI 能力

沟通表达（从简历推断）

每项给：

Score

Reason

Evidence

优势分析

例如：

具有大型分布式系统经验

云原生经验丰富

拥有 AI Agent 开发经验

工程质量较高

风险分析

例如：

缺少高并发项目

缺少监控体系

没有性能优化案例

项目描述过于笼统

职责疑似夸大

技术跨度异常

时间线存在冲突

工作经历存在空档

等等。

面试建议

生成：

值得重点追问的问题

可能存在夸大的地方

建议深入验证的问题

建议跳过的问题

综合评价

生成最终 Summary。

例如：

适合高级后端岗位。

偏工程型。

分布式经验较好。

AI 能力属于应用层。

适合作为二面候选人。

八、JD Matching（下一阶段）

支持：

输入 JD。

输出：

Skill Match

Missing Skills

Risk

Gap

Recommendation

Match Score

九、Interview Agent（下一阶段）

基于：

Resume

JD

自动生成：

技术问题

项目问题

开放问题

行为问题

压力问题

追问链路

并支持：

根据候选人回答继续追问。
