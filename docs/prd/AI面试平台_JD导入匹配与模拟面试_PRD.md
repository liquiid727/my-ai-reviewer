# AI 面试平台：JD 导入、简历匹配与模拟面试 PRD

> 文档版本：v1.0
> 文档状态：初稿
> 更新时间：2026-08-05
> 适用产品：AI 面试平台 / JobAgent
> 主要模块：JD 资料库、简历与 JD 匹配、模拟面试创建、模拟面试运行、面试报告

---

## 1. 文档概述

### 1.1 产品背景

当前平台已具备以下基础能力：

- 简历上传与解析
- 简历事实与候选人画像抽取
- 简历多维评估
- 文字 AI 面试
- 回答评分与动态追问
- JD 结构化识别
- JD 资料库存储能力

现有链路中，JD 资料的导入、确认、版本管理，以及“简历 + JD → 匹配分析 → 创建模拟面试 → 进入面试 → 生成报告”的完整业务流程仍不完整。

本 PRD 用于定义一套完整且可扩展的业务链路，使用户能够：

1. 通过文本、文件、图片、链接等方式导入 JD；
2. 自动提取并确认岗位结构化信息；
3. 选择简历与 JD 进行匹配度分析；
4. 基于匹配结果创建特定场景的模拟面试；
5. 在结构化面试流程中完成问答、追问与评分；
6. 获得岗位适配、面试表现和学习提升建议。

---

## 2. 产品目标

### 2.1 核心目标

建立以下四个相互独立但可串联的产品模块：

1. **JD 资料库**
2. **简历与 JD 匹配评估**
3. **模拟面试创建与场景配置**
4. **模拟面试运行与报告**

### 2.2 用户价值

用户可以围绕真实目标岗位，形成完整求职训练闭环：

```text
导入 JD
→ 结构化识别
→ 选择简历
→ 匹配度评估
→ 发现能力缺口
→ 创建模拟面试
→ 完成面试
→ 获取报告
→ 生成学习与优化计划
```

### 2.3 产品原则

1. 创建面试与开始面试必须拆分；
2. 所有匹配与面试结果必须绑定简历版本和 JD 版本；
3. 所有重要判断尽量提供证据；
4. 采用“预生成面试计划 + 动态追问”的混合模式；
5. 面试官、评分器、检索器、流程控制器逻辑分离；
6. RAG 负责提供事实，Agent 负责决策；
7. 不将整场面试仅保存为一段聊天记录；
8. 所有模型输出均需采用结构化数据契约。

---

## 3. 产品范围

### 3.1 本期范围

#### JD 模块

- 文本导入
- 文件导入
- 图片导入
- 公开链接导入
- 手动创建
- JD 内容清洗
- JD 结构化识别
- 置信度与证据保存
- 人工确认与修改
- 失败重试
- 重新识别
- 版本管理
- 重复检测

#### 简历匹配模块

- 选择简历版本
- 选择 JD 版本
- 多维匹配评分
- 硬性条件判断
- 技能与项目证据分析
- 能力缺口分类
- 匹配报告
- 从匹配报告创建模拟面试

#### 模拟面试模块

- 综合模拟面试
- 技术一面
- 项目深挖
- 文字面试
- 面试时长配置
- 难度配置
- 动态追问
- 暂停、恢复、跳过、结束
- 单题评分
- 最终报告

### 3.2 暂不纳入本期

- 视频面试
- 数字人面试官
- 多面试官群面
- 企业招聘端
- 公司内部私有知识库
- 白板协作
- 实时代码编辑器
- 浏览器插件
- 自动投递
- 自动抓取登录态招聘页面

---

## 4. 用户角色

### 4.1 求职用户

主要行为：

- 上传和管理简历
- 导入目标岗位 JD
- 选择简历和 JD 进行匹配
- 创建模拟面试
- 完成面试
- 查看报告
- 生成学习计划与求职任务

### 4.2 平台管理员

主要行为：

- 管理 JD 解析任务
- 管理面试场景模板
- 管理题库和评分规则
- 查看模型调用和异常
- 管理解析器、Prompt、Schema 版本
- 查看系统运行指标和评测结果

---

## 5. 整体业务流程

```mermaid
flowchart LR
    A[导入 JD] --> B[内容提取]
    B --> C[JD 结构化识别]
    C --> D[用户确认和修正]
    D --> E[保存 JD 版本]

    E --> F[选择简历版本]
    F --> G[简历与 JD 匹配分析]
    G --> H[查看匹配报告]

    H --> I[创建模拟面试]
    I --> J[选择面试场景]
    J --> K[生成面试方案]
    K --> L[用户确认]

    L --> M[开始模拟面试]
    M --> N[基础问题]
    N --> O[动态追问]
    O --> P[结束面试]
    P --> Q[生成面试报告]
    Q --> R[生成提升计划]
```

---

# 6. PRD 一：JD 导入与职位资料库

## 6.1 功能目标

支持用户通过多种方式导入职位描述，平台完成：

1. 原始内容获取；
2. 文本清洗与标准化；
3. JD 结构化解析；
4. 证据和置信度记录；
5. 用户校正；
6. 版本化存储；
7. 为匹配与面试提供标准输入。

---

## 6.2 JD 导入方式

| 导入方式 | 使用场景 | 处理方式 |
|---|---|---|
| 粘贴文本 | 用户复制招聘网站内容 | 直接清洗和解析 |
| 上传文件 | PDF、DOCX、TXT、MD、HTML | 文件解析后识别 |
| 上传图片 | 招聘软件截图、聊天截图 | OCR 或视觉模型识别后解析 |
| 输入链接 | 公司官网、公开招聘页面 | 抓取页面正文 |
| 手动创建 | 内容较少或需要补充 | 表单填写 |

### 6.2.1 链接导入限制提示

产品文案：

> 支持公开可访问的职位链接。部分需要登录、存在访问限制或动态加载的网站可能无法自动获取，请改用粘贴文本、上传截图或上传文件。

---

## 6.3 导入流程

### 第一步：选择导入方式

入口：

```text
导入 JD
```

方式：

- 粘贴文本
- 上传文件
- 上传图片
- 输入链接
- 手动填写

### 第二步：补充来源信息

系统自动识别失败时，允许用户填写：

- 岗位名称
- 公司名称
- 来源平台
- 原始链接
- 工作地点
- 薪资范围
- 备注
- 标签

### 第三步：系统处理

展示阶段状态：

```text
正在读取内容
正在清理职位文本
正在识别岗位要求
正在生成结构化职位信息
```

### 第四步：确认识别结果

用户可查看并修改：

- 岗位名称
- 公司名称
- 部门
- 岗位职责
- 必须技能
- 优先技能
- 工作年限
- 学历要求
- 职级
- 薪资范围
- 工作地点
- 行业方向
- 产品方向
- 业务场景
- 加分项
- 证书要求
- 语言要求
- 其他要求

### 第五步：保存

保存后进入 JD 详情页。

详情页支持：

- 查看原始内容
- 查看结构化信息
- 修改识别结果
- 重新解析
- 查看解析证据
- 创建新版本
- 匹配简历
- 创建模拟面试
- 归档
- 删除

---

## 6.4 JD 标准数据结构

```json
{
  "jd_id": "jd_xxx",
  "version": 1,
  "source": {
    "type": "url",
    "platform": "company_official",
    "url": "https://example.com/job/123",
    "file_name": null,
    "content_hash": "sha256_xxx",
    "imported_at": "2026-08-05T10:00:00+08:00"
  },
  "job": {
    "title": "AI Agent 开发工程师",
    "company_name": "示例科技",
    "department": "AI 应用部",
    "location": ["杭州"],
    "employment_type": "full_time",
    "seniority": "mid",
    "salary": {
      "min": 25000,
      "max": 40000,
      "months": 14,
      "currency": "CNY"
    }
  },
  "requirements": {
    "years_of_experience": {
      "min": 3,
      "max": 5
    },
    "education": "本科",
    "required_skills": [
      {
        "name": "Python",
        "importance": 0.95,
        "evidence": "负责基于 Python 构建 Agent 应用",
        "confidence": 0.98,
        "source_position": {
          "start": 128,
          "end": 154
        }
      }
    ],
    "preferred_skills": [],
    "domain_experience": [],
    "language_requirements": [],
    "certifications": []
  },
  "responsibilities": [],
  "business_context": {
    "industry": "人工智能",
    "product_type": "企业级 Agent 平台",
    "target_users": ["企业客户"],
    "business_keywords": []
  },
  "interview_clues": {
    "likely_focus": [
      "Agent 架构",
      "RAG",
      "工具调用",
      "生产部署"
    ],
    "possible_system_design_topics": [],
    "possible_project_topics": []
  },
  "metadata": {
    "parser_version": "jd-parser-v1",
    "model": "model-name",
    "schema_version": "1.0",
    "overall_confidence": 0.91,
    "status": "confirmed"
  }
}
```

### 6.4.1 字段设计原则

重要字段应尽量包含：

- value
- confidence
- evidence
- source_position
- source_type
- model_version
- parser_version

---

## 6.5 JD 状态机

```text
draft
  ↓
uploaded
  ↓
extracting
  ↓
extracted
  ↓
parsing
  ↓
needs_review
  ↓
confirmed
  ↓
ready
```

异常状态：

```text
extract_failed
parse_failed
unsupported
duplicate
archived
deleted
```

### 6.5.1 状态说明

| 状态 | 说明 |
|---|---|
| draft | 用户正在编辑，未提交 |
| uploaded | 原始内容已上传 |
| extracting | 正在提取文本 |
| extracted | 文本提取完成 |
| parsing | 正在结构化识别 |
| needs_review | 已识别，但需要用户确认 |
| confirmed | 用户已确认 |
| ready | 可用于匹配与面试 |
| extract_failed | 文本提取失败 |
| parse_failed | 结构化识别失败 |
| unsupported | 不支持的文件或链接 |
| duplicate | 检测到重复内容 |
| archived | 已归档 |
| deleted | 已删除 |

---

## 6.6 重复检测

重复判断依据：

1. 原始链接完全相同；
2. 文件哈希相同；
3. 标准化文本哈希相同；
4. 公司 + 岗位名称 + 地点高度相似；
5. 文本向量相似度超过阈值。

处理方式：

- 提示已存在相同 JD；
- 允许打开已有 JD；
- 允许创建新版本；
- 不建议默认创建重复记录。

---

## 6.7 JD 列表页

### 6.7.1 页面元素

- 搜索框
- 来源筛选
- 状态筛选
- 公司筛选
- 标签筛选
- 导入 JD
- 创建匹配分析

### 6.7.2 列表项信息

```text
AI Agent 开发工程师
某某科技 · 杭州 · 3-5 年

必须技能：Python / RAG / Agent / LangGraph
来源：官方网站
状态：已确认
更新时间：2 小时前
```

### 6.7.3 列表项操作

- 查看详情
- 匹配简历
- 创建面试
- 重新解析
- 编辑
- 归档
- 删除

### 6.7.4 空状态文案

标题：

> 还没有职位描述

说明：

> 导入职位描述，系统会自动识别岗位职责、技能要求和面试重点。

按钮：

```text
导入 JD
```

---

# 7. PRD 二：简历与 JD 匹配评估

## 7.1 功能目标

允许用户选择一份简历版本和一份 JD 版本，生成可解释、可复现、可追溯的岗位匹配报告。

---

## 7.2 功能入口

提供三个入口：

1. JD 详情页：匹配简历
2. 简历详情页：匹配职位
3. 独立匹配中心：创建匹配分析

三个入口统一进入：

```text
选择简历版本
+
选择 JD 版本
+
开始匹配分析
```

---

## 7.3 匹配输入

必须输入：

- resume_id
- resume_version_id
- jd_id
- jd_version_id

可选输入：

- 目标面试轮次
- 用户补充说明
- 是否使用历史匹配缓存
- 是否生成简历优化建议
- 是否生成面试重点

---

## 7.4 匹配评分维度

| 维度 | 建议权重 |
|---|---:|
| 必须技能匹配 | 25 |
| 工作经验与年限 | 15 |
| 项目经历匹配 | 20 |
| 岗位职责相关度 | 15 |
| 技术栈与工具 | 10 |
| 行业和业务经验 | 5 |
| 学历、地点等基础要求 | 5 |
| 优先项与加分项 | 5 |

总分：100 分。

---

## 7.5 强约束规则

示例：

```text
缺失核心必须技能：
总分上限为 75

工作年限严重不足：
总分上限为 70

明确要求特定证书但用户不具备：
标记为硬性风险

学历要求不满足：
标记为风险，是否封顶由岗位规则决定

地点不匹配但支持远程：
不作为硬性扣分项
```

规则由后台配置，不全部交由 LLM 判断。

---

## 7.6 匹配技术方案

采用混合评分：

```text
规则匹配
+
技能标准化
+
Embedding 语义匹配
+
LLM 证据判断
+
加权评分器
```

### 7.6.1 规则引擎

负责：

- 工作年限
- 学历
- 地点
- 证书
- 语言
- 工作类型
- 职级
- 薪资
- 硬性条件

### 7.6.2 技能标准化

处理：

- Go / Golang
- PostgreSQL / Postgres
- Kubernetes / K8s
- Large Language Model / LLM
- Retrieval-Augmented Generation / RAG

### 7.6.3 Embedding 语义匹配

用于：

- 项目经历与岗位职责匹配
- 行业描述匹配
- 技术场景匹配
- 同义表达匹配

### 7.6.4 LLM 证据判断

负责判断：

- 简历内容是否真的能证明技能；
- 项目经验是否满足岗位要求；
- 是否存在表达缺口；
- 是否存在证据不足；
- 是否存在夸大或矛盾风险。

### 7.6.5 评分器

负责：

- 汇总子项得分；
- 应用权重；
- 应用上限规则；
- 生成总分；
- 生成推荐等级。

---

## 7.7 能力缺口分类

匹配报告必须区分：

1. **真实能力缺口**
2. **简历表达缺口**
3. **证据不足**
4. **硬性条件风险**
5. **尚未验证**
6. **优先项缺失**

示例文案：

错误：

> 你不会 Redis。

正确：

> 当前简历中未找到能够证明 Redis 实践经验的具体内容。

---

## 7.8 匹配报告页面

### 7.8.1 总体结论

```text
综合匹配度：78/100
推荐程度：值得投递，但需要针对性优化
```

### 7.8.2 维度评分

可使用雷达图或条形评分：

- 必须技能
- 项目经历
- 工作经验
- 岗位职责
- 技术栈
- 业务经验
- 基础条件
- 加分项

### 7.8.3 已匹配能力

每项展示：

- JD 要求
- 简历证据
- 匹配结论
- 得分
- 置信度
- 证据位置

### 7.8.4 能力缺口

每项展示：

- 缺口类型
- 重要程度
- 影响
- 当前证据
- 建议行动

### 7.8.5 下一步行动

- 优化当前简历
- 生成针对性简历
- 创建模拟面试
- 生成学习计划
- 添加到求职计划

---

## 7.9 匹配状态机

```text
created
  ↓
queued
  ↓
processing
  ↓
completed
```

异常状态：

```text
failed
cancelled
expired
outdated
```

当简历版本或 JD 版本发生变化时，原匹配报告标记为：

```text
outdated
```

---

# 8. PRD 三：模拟面试创建与场景配置

## 8.1 功能目标

在开始正式模拟面试前，基于简历、JD、匹配报告和面试场景，生成一份结构化、可执行的面试方案。

---

## 8.2 创建面试入口

入口包括：

- JD 详情页
- 简历详情页
- 匹配报告页
- 面试列表页
- 求职计划任务页

推荐主入口：

```text
匹配报告 → 创建模拟面试
```

---

## 8.3 创建面试输入

### 8.3.1 基础材料

- 简历版本
- JD 版本
- 匹配报告，可选但建议默认使用

### 8.3.2 面试场景

- 综合模拟面试
- HR 初筛
- 技术一面
- 项目深挖
- 系统设计
- 行为面试
- 主管面试
- 自定义专项面试

### 8.3.3 面试配置

- 面试时长：15 / 30 / 45 / 60 分钟
- 难度：基础 / 标准 / 挑战
- 模式：文字 / 语音
- 语言：中文 / 英文
- 追问强度：温和 / 标准 / 深挖
- 是否提供即时提示
- 是否允许跳过
- 是否展示阶段进度
- 是否开启压力面试风格

### 8.3.4 MVP 配置

首版仅开放：

- 面试场景
- 面试时长
- 难度
- 文字或语音

其他配置使用场景默认值。

---

## 8.4 Interview Scenario 结构

面试场景必须为结构化配置，而不是一段 Prompt。

```yaml
scenario_id: technical_first_round
name: 技术一面
description: 验证候选人的核心技术能力和项目真实性

default_duration_minutes: 40
difficulty: standard

interviewer:
  role: senior_engineer
  tone: professional
  pressure_level: medium

stages:
  - type: opening
    duration_minutes: 3
    goals:
      - 建立面试上下文
      - 让候选人进行自我介绍

  - type: resume_verification
    duration_minutes: 10
    goals:
      - 验证核心项目真实性
      - 确认候选人的实际职责

  - type: jd_skill_assessment
    duration_minutes: 15
    goals:
      - 覆盖 JD 必须技能
      - 验证技术深度

  - type: problem_solving
    duration_minutes: 8
    goals:
      - 验证分析能力
      - 验证方案权衡能力

  - type: candidate_questions
    duration_minutes: 4
    goals:
      - 模拟真实反问环节

competencies:
  - technical_depth
  - project_ownership
  - problem_solving
  - communication

follow_up_policy:
  max_depth: 2
  trigger_conditions:
    - answer_is_vague
    - evidence_is_missing
    - important_claim_needs_verification
    - answer_reveals_high_value_topic

scoring:
  scale: 5
  dimensions:
    - correctness
    - depth
    - evidence
    - structure
    - communication
```

---

## 8.5 场景模板建议

### 8.5.1 综合模拟面试

目标：

- 模拟完整面试流程
- 综合评估岗位适配度
- 覆盖简历、JD 和通用能力

阶段：

1. 自我介绍
2. 求职动机
3. 项目经历
4. JD 核心技能
5. 场景题
6. 行为问题
7. 候选人反问

### 8.5.2 技术一面

目标：

- 验证核心技术能力
- 验证基础知识
- 验证项目真实性
- 验证问题解决能力

### 8.5.3 项目深挖

目标：

- 判断项目是否真实
- 判断个人贡献
- 判断技术深度
- 判断方案权衡
- 判断结果验证能力

典型追问链：

```text
你做了什么
→ 为什么这么做
→ 具体如何实现
→ 遇到了什么问题
→ 如何验证结果
→ 有没有其他方案
```

### 8.5.4 HR 初筛

目标：

- 求职动机
- 离职原因
- 薪资预期
- 工作地点
- 稳定性
- 沟通表达
- 职业规划

### 8.5.5 系统设计

目标：

- 需求澄清
- 架构设计
- 数据模型
- 高并发
- 一致性
- 可用性
- 可观测性
- 成本权衡

---

# 9. Interview Plan 面试方案

## 9.1 功能说明

创建面试后，系统先生成 Interview Plan，用户确认后再开始面试。

### 9.1.1 计划摘要

```text
预计时长：35 分钟
预计问题：8 个主问题
最多追问：12 个

重点考察：
1. Go 并发和服务治理
2. Agent 状态管理
3. RAG 召回和评估
4. 项目真实性与个人贡献

风险验证：
1. JD 要求 3 年 Agent 经验，简历中的相关经历不足
2. 简历提到 LangGraph，但缺少生产环境说明
3. JD 要求评测体系，需要验证实际经验
```

---

## 9.2 计划问题结构

```json
{
  "question_id": "q_001",
  "stage": "project_deep_dive",
  "competency": "project_ownership",
  "question": "请介绍你在 Agent 项目中的具体职责。",
  "purpose": "验证项目真实性和个人贡献",
  "source": {
    "type": "resume",
    "reference_id": "project_003"
  },
  "expected_signals": [
    "能够明确区分团队工作和个人工作",
    "能够说明技术决策",
    "能够说明遇到的问题"
  ],
  "risk_signals": [
    "只描述团队成果",
    "无法说明个人负责模块",
    "无法解释关键技术决策"
  ],
  "follow_up_candidates": [],
  "scoring_rubric": {
    "correctness": 5,
    "depth": 5,
    "evidence": 5,
    "structure": 5,
    "communication": 5
  }
}
```

---

## 9.3 问题来源

问题可来自：

- 简历事实
- JD 必须技能
- JD 优先技能
- 匹配报告缺口
- 项目经历
- 公共题库
- 面试场景模板
- 历史回答
- 动态追问

---

## 9.4 计划生成策略

建议：

```text
70% 预生成问题
+
30% 根据用户回答动态调整
```

预生成部分保证：

- 面试覆盖率
- 时长控制
- 评分一致性
- 场景稳定性

动态部分保证：

- 对话自然
- 深度追问
- 风险验证
- 高价值信息探索

---

# 10. PRD 四：模拟面试运行

## 10.1 功能目标

按照 Interview Plan 和 Interview Scenario 执行模拟面试，支持阶段控制、动态追问、回答评分、暂停恢复和最终报告。

---

## 10.2 面试阶段

### 阶段 1：面试准备

- 检查简历和 JD 状态；
- 检查版本是否有效；
- 构建会话上下文；
- 载入场景模板；
- 载入面试计划；
- 初始化评分规则；
- 初始化问题覆盖矩阵；
- 记录模型和 Prompt 版本。

### 阶段 2：开场

- 说明面试场景；
- 说明预计时长；
- 提醒用户可以暂停或结束；
- 说明回答方式；
- 发起自我介绍问题。

### 阶段 3：基础验证

围绕：

- 求职动机
- 当前职责
- 核心经历
- 岗位关联
- 工作年限
- 职业方向

### 阶段 4：项目深挖

按照追问链：

```text
做了什么
→ 为什么做
→ 如何实现
→ 遇到什么问题
→ 如何解决
→ 如何验证
→ 有何替代方案
```

### 阶段 5：JD 专项考察

优先覆盖：

1. JD 必须技能；
2. 匹配报告中的高风险项；
3. 简历中声称但证据不足的能力；
4. 高价值项目经历；
5. 尚未验证的岗位要求。

### 阶段 6：综合题或场景题

例如：

- 系统设计
- 故障排查
- 技术选型
- 业务建模
- 性能优化
- 团队协作
- 冲突处理

### 阶段 7：候选人反问

允许用户提出 1～3 个问题。

系统可评价反问质量，但不得虚构公司内部信息。

### 阶段 8：结束与报告生成

- 结束会话；
- 异步聚合评分；
- 生成能力报告；
- 生成岗位适配结论；
- 生成学习建议；
- 生成下一次专项面试建议。

---

## 10.3 面试运行状态机

```text
draft
  ↓
preparing
  ↓
ready
  ↓
in_progress
  ├── paused
  │     ↓
  │   in_progress
  ↓
completing
  ↓
completed
```

异常状态：

```text
cancelled
failed
expired
terminated
```

---

## 10.4 问题状态

```text
planned
asked
answered
evaluating
evaluated
followed_up
skipped
abandoned
```

---

## 10.5 面试操作

用户操作：

- 提交回答
- 暂停
- 恢复
- 跳过问题
- 重新录入
- 提前结束
- 查看当前进度
- 退出并稍后继续

系统操作：

- 生成下一问题
- 判断是否追问
- 切换面试阶段
- 更新覆盖矩阵
- 对回答评分
- 保存事件
- 判断是否结束

---

## 10.6 动态追问规则

触发条件：

- 回答过于模糊；
- 缺少具体证据；
- 重要结论未验证；
- 回答存在矛盾；
- 回答出现高价值技术点；
- 用户声称负责核心模块；
- 回答与简历事实不一致；
- 关键技能尚未充分验证。

终止条件：

- 达到最大追问深度；
- 已获得充分证据；
- 用户无法继续回答；
- 时间预算不足；
- 当前能力项已完成评估；
- 连续两次回答无新增信息。

MVP 默认：

```text
最大追问深度：2
单个主问题最多追问：2 次
```

---

# 11. Agent 与 RAG 架构设计

## 11.1 逻辑角色

### 11.1.1 Interview Orchestrator

负责：

- 控制面试阶段；
- 控制时长；
- 选择下一题；
- 判断是否追问；
- 判断是否切换阶段；
- 判断是否结束；
- 更新问题覆盖矩阵。

适合使用 LangGraph 状态机。

### 11.1.2 Interviewer

负责：

- 用自然语言提问；
- 根据场景调整语气；
- 根据回答生成追问；
- 保持上下文连贯；
- 避免重复问题。

### 11.1.3 Answer Evaluator

负责：

- 对单次回答评分；
- 提取关键观点；
- 判断完整度；
- 判断真实性信号；
- 判断矛盾；
- 生成追问信号；
- 输出结构化评估结果。

### 11.1.4 Retrieval Layer

负责检索：

- 简历事实；
- JD 要求；
- 匹配报告；
- 历史回答；
- 问题库；
- 评分 Rubric；
- 行业知识；
- 场景模板。

### 11.1.5 Report Generator

负责：

- 汇总单题评分；
- 聚合能力维度；
- 输出优势和风险；
- 生成改进建议；
- 生成学习计划；
- 生成下次面试建议。

---

## 11.2 MVP 实现建议

首版不必部署为多个独立 Agent。

建议实现为一套 LangGraph 工作流：

```text
Orchestrator Node
Interviewer Node
Evaluator Node
Retriever Node
Report Node
```

每个节点使用：

- 独立 Prompt
- 独立输入输出 Schema
- 独立日志
- 独立错误处理
- 独立模型配置
- 独立评测指标

---

## 11.3 RAG 分层

### 第一层：用户私有上下文

- 简历事实
- 项目经历
- 技能
- JD 内容
- 匹配报告
- 当前会话回答

### 第二层：平台面试能力库

- 岗位能力模型
- 面试题库
- 追问模板
- 评分 Rubric
- 优秀回答信号
- 风险信号
- 常见错误
- 答题框架

### 第三层：行业和公司资料

- 公司公开介绍
- 产品信息
- 行业术语
- 技术栈
- 公开面试经验

MVP 优先实现前两层。

---

# 12. 问题覆盖矩阵

每场面试维护一张内部覆盖矩阵。

| 能力项 | 来源 | 重要性 | 是否已提问 | 得分 | 证据充分度 |
|---|---|---:|---|---:|---|
| Go 并发 | JD 必须技能 | 高 | 是 | 4 | 高 |
| Agent 状态机 | JD 职责 | 高 | 是 | 3 | 中 |
| RAG 评测 | 匹配缺口 | 高 | 是 | 2 | 低 |
| 项目负责程度 | 简历项目 | 中 | 是 | 4 | 高 |
| 沟通表达 | 通用能力 | 中 | 是 | 3 | 中 |

Orchestrator 根据覆盖矩阵决定：

- 下一题问什么；
- 是否追问；
- 是否切换阶段；
- 哪些能力尚未验证；
- 是否提前结束。

---

# 13. 单题回答评估

## 13.1 评分维度

建议采用 5 分制：

| 维度 | 说明 |
|---|---|
| correctness | 内容是否正确 |
| depth | 是否有足够技术深度 |
| evidence | 是否提供具体事实或案例 |
| structure | 表达是否有结构 |
| communication | 是否清晰、简洁、易理解 |
| relevance | 是否切中问题 |
| ownership | 是否能说明个人贡献 |
| tradeoff | 是否体现方案权衡 |

不同场景可以启用不同维度。

---

## 13.2 单题评估输出

```json
{
  "answer_id": "ans_xxx",
  "score": 3.6,
  "dimension_scores": {
    "correctness": 4,
    "depth": 3,
    "evidence": 3,
    "structure": 4,
    "communication": 4
  },
  "summary": "候选人能够说明基本方案，但缺少性能数据和失败案例。",
  "strengths": [
    "说明了核心技术方案",
    "能够解释个人职责"
  ],
  "weaknesses": [
    "缺少量化结果",
    "没有说明替代方案"
  ],
  "evidence": [
    "负责 LangGraph 状态持久化和动态追问"
  ],
  "risk_signals": [
    "无法说明线上问题和监控指标"
  ],
  "follow_up_required": true,
  "follow_up_reason": "需要验证生产环境经验"
}
```

---

# 14. 面试报告

## 14.1 总体结果

```text
综合表现：72/100
岗位适配建议：可以继续准备后投递
模拟轮次：技术一面
```

---

## 14.2 能力维度

- 技术正确性
- 技术深度
- 项目真实性
- 项目负责程度
- 问题分析
- 方案权衡
- 表达结构
- 沟通能力
- 岗位适配度

---

## 14.3 高表现问题

展示：

- 问题
- 用户回答摘要
- 优秀点
- 对应能力证据
- 得分

---

## 14.4 薄弱问题

展示：

- 问题
- 回答缺口
- 为什么不足
- 推荐答题结构
- 建议练习内容
- 示例改进方向

---

## 14.5 JD 覆盖情况

```text
已验证必须能力：6/8
表现良好：3
基本满足：2
存在风险：1
尚未验证：2
```

---

## 14.6 下一步计划

- 修改简历
- 补充项目数据
- 学习特定知识点
- 重新练习薄弱问题
- 创建专项面试
- 加入求职 Todo
- 生成投递前检查清单

---

# 15. 页面与交互设计

## 15.1 JD 列表页

顶部：

- 页面标题
- 搜索
- 来源筛选
- 状态筛选
- 导入 JD
- 创建匹配分析

列表卡片：

- 岗位名称
- 公司名称
- 地点
- 工作年限
- 核心技能
- 来源
- 状态
- 更新时间

操作：

- 查看详情
- 匹配简历
- 创建面试
- 更多

---

## 15.2 JD 详情页

模块：

1. 岗位概览
2. 原始 JD
3. 结构化内容
4. 技能要求
5. 岗位职责
6. 业务背景
7. 面试重点
8. 解析证据
9. 版本历史

主要操作：

- 编辑
- 重新解析
- 匹配简历
- 创建模拟面试
- 归档

---

## 15.3 匹配创建页

布局：

```text
左侧：选择简历版本
右侧：选择 JD 版本
底部：开始匹配分析
```

辅助信息：

- 简历更新时间
- JD 更新时间
- 是否存在历史匹配
- 是否已过期

---

## 15.4 匹配报告页

页面结构：

1. 总体匹配度
2. 维度评分
3. 已匹配能力
4. 能力缺口
5. 硬性风险
6. 简历优化建议
7. 面试重点
8. 下一步行动

主按钮：

```text
创建模拟面试
```

次按钮：

- 优化简历
- 生成学习计划
- 加入求职计划

---

## 15.5 创建模拟面试页

步骤：

1. 确认简历和 JD
2. 选择面试场景
3. 配置时长和难度
4. 生成面试方案
5. 确认并开始

---

## 15.6 面试准备页

展示：

- 面试岗位
- 使用简历
- 面试场景
- 预计时长
- 重点能力
- 风险验证
- 问题数量
- 追问策略

按钮：

```text
开始面试
```

---

## 15.7 面试运行页

建议布局：

### 左侧

- 当前阶段
- 面试进度
- 已用时间
- 能力覆盖情况

### 中间

- 面试官问题
- 用户输入框
- 语音入口
- 提交回答

### 右侧

- 简历摘要
- JD 摘要
- 当前问题目标
- 暂停
- 跳过
- 结束面试

注意：

- 默认不向用户展示内部评分 Rubric；
- 可展示“当前阶段”和“总体进度”；
- 即时评分作为可选模式。

---

# 16. 核心数据库实体

## 16.1 JD 相关

```text
job_descriptions
job_description_versions
job_description_sources
job_description_parse_runs
job_description_fields
job_description_evidence
```

## 16.2 匹配相关

```text
resume_jd_matches
match_dimensions
match_requirements
match_evidence
match_recommendations
```

## 16.3 面试场景与计划

```text
interview_scenarios
interview_scenario_versions
interview_templates
interview_plans
interview_plan_stages
interview_plan_questions
```

## 16.4 面试运行

```text
interview_sessions
interview_questions
interview_answers
answer_evaluations
interview_events
interview_reports
interview_report_dimensions
```

---

## 16.5 关键字段

### interview_sessions

```text
id
user_id
resume_id
resume_version_id
jd_id
jd_version_id
match_id
scenario_id
scenario_version
plan_id
status
mode
language
difficulty
duration_minutes
started_at
paused_at
completed_at
model_config_snapshot
prompt_version
schema_version
created_at
updated_at
```

### interview_questions

```text
id
session_id
plan_question_id
parent_question_id
stage
question_type
question_text
purpose
source_type
source_reference_id
status
sequence_no
asked_at
created_at
```

### interview_answers

```text
id
session_id
question_id
content
audio_url
duration_seconds
submitted_at
created_at
```

### answer_evaluations

```text
id
answer_id
overall_score
dimension_scores
strengths
weaknesses
risk_signals
evidence
follow_up_required
follow_up_reason
model_name
prompt_version
created_at
```

---

# 17. 事件模型

必须使用 `interview_events` 记录面试过程。

事件示例：

```text
session.created
plan.generated
session.started
stage.entered
question.asked
answer.submitted
answer.evaluated
followup.generated
question.skipped
session.paused
session.resumed
session.completed
report.generated
session.failed
```

事件字段：

```text
id
session_id
event_type
event_version
payload
trace_id
request_id
created_at
```

用途：

- 会话恢复
- 问题回放
- 故障排查
- Agent Eval
- 成本统计
- 行为分析
- 审计

---

# 18. API 草案

## 18.1 JD

```http
POST   /api/v1/job-descriptions/import/text
POST   /api/v1/job-descriptions/import/file
POST   /api/v1/job-descriptions/import/image
POST   /api/v1/job-descriptions/import/url
POST   /api/v1/job-descriptions/manual

GET    /api/v1/job-descriptions
GET    /api/v1/job-descriptions/{id}
GET    /api/v1/job-descriptions/{id}/versions
PUT    /api/v1/job-descriptions/{id}
POST   /api/v1/job-descriptions/{id}/reparse
POST   /api/v1/job-descriptions/{id}/confirm
POST   /api/v1/job-descriptions/{id}/archive
DELETE /api/v1/job-descriptions/{id}
```

## 18.2 匹配

```http
POST /api/v1/resume-jd-matches
GET  /api/v1/resume-jd-matches
GET  /api/v1/resume-jd-matches/{id}
POST /api/v1/resume-jd-matches/{id}/rerun
```

## 18.3 面试场景

```http
GET  /api/v1/interview-scenarios
GET  /api/v1/interview-scenarios/{id}
```

## 18.4 面试计划

```http
POST /api/v1/interview-plans
GET  /api/v1/interview-plans/{id}
POST /api/v1/interview-plans/{id}/regenerate
POST /api/v1/interview-plans/{id}/confirm
```

## 18.5 面试运行

```http
POST /api/v1/interview-sessions
GET  /api/v1/interview-sessions
GET  /api/v1/interview-sessions/{id}

POST /api/v1/interview-sessions/{id}/start
POST /api/v1/interview-sessions/{id}/answers
POST /api/v1/interview-sessions/{id}/pause
POST /api/v1/interview-sessions/{id}/resume
POST /api/v1/interview-sessions/{id}/skip
POST /api/v1/interview-sessions/{id}/complete
POST /api/v1/interview-sessions/{id}/cancel

GET  /api/v1/interview-sessions/{id}/events
GET  /api/v1/interview-sessions/{id}/report
```

---

# 19. 非功能需求

## 19.1 可追溯性

所有结果需记录：

- resume_version
- jd_version
- scenario_version
- prompt_version
- model_version
- parser_version
- schema_version

## 19.2 幂等性

以下操作需支持幂等：

- JD 导入
- JD 解析
- 匹配分析
- 面试计划生成
- 回答提交
- 回答评分
- 报告生成

## 19.3 超时与重试

- 文件解析超时
- 链接抓取超时
- LLM 调用超时
- Embedding 调用超时
- 评分失败重试
- 报告生成失败重试

## 19.4 安全与隐私

- 简历和 JD 默认仅用户本人可见；
- 企业公开 JD 和用户私有信息分离；
- 模型调用内容需按平台隐私策略处理；
- 日志不得记录完整身份证号、手机号、邮箱等敏感信息；
- 删除简历或 JD 时应处理关联向量和缓存；
- 用户可删除面试录音和面试记录。

## 19.5 可观测性

核心指标：

- JD 导入成功率
- JD 解析成功率
- JD 平均处理耗时
- 匹配分析成功率
- 匹配平均耗时
- 面试计划生成成功率
- 面试完成率
- 平均面试时长
- 平均追问次数
- 报告生成成功率
- LLM Token 消耗
- 单场面试成本
- 模型错误率
- 用户主动退出率

---

# 20. Agent Eval

## 20.1 JD 解析评测

指标：

- 字段准确率
- 必须技能召回率
- 优先技能准确率
- 职责切分准确率
- 工作年限准确率
- 公司和岗位名称准确率
- 证据定位准确率
- 结构化输出合法率

## 20.2 匹配评测

指标：

- 硬性条件判断准确率
- 技能匹配准确率
- 项目证据准确率
- 缺口分类准确率
- 分数稳定性
- 同版本重复运行偏差
- 人工评审一致性

## 20.3 面试评测

指标：

- 问题与岗位相关度
- 简历事实引用准确率
- 重复问题率
- 追问合理性
- 能力覆盖率
- 面试阶段完成率
- 评分一致性
- 报告与单题评分一致性
- 幻觉率
- 超时率
- 死循环率

---

# 21. MVP 版本计划

## 21.1 MVP

### JD

- 文本导入
- 文件导入
- 图片导入
- 公开链接导入
- 自动结构化解析
- 证据和置信度
- 人工确认
- 重试
- 重新解析
- 版本管理

### 匹配

- 选择简历和 JD
- 8 个维度评分
- 必须技能缺口
- 证据展示
- 推荐结论
- 面试重点生成

### 面试

- 综合模拟
- 技术一面
- 项目深挖
- 文字模式
- 15 / 30 / 45 分钟
- 基础 / 标准 / 挑战
- 最多两轮动态追问
- 单题评分
- 最终报告
- 暂停
- 恢复
- 提前结束

---

## 21.2 P1

- 语音面试
- 自定义面试场景
- 公司公开资料 RAG
- 系统设计专项
- 历史能力趋势
- 专项训练模式
- 即时反馈模式
- 面试回放

---

## 21.3 P2

- 视频面试
- 数字人面试官
- 多角色面试
- 群面模拟
- 企业真实流程模板
- 企业招聘端
- 浏览器插件
- 自动采集招聘网站内容

---

# 22. 验收标准

## 22.1 JD 导入

- 用户可以通过文本、文件、图片、链接创建 JD；
- 系统可以生成结构化字段；
- 用户可以修改并确认字段；
- 系统可以保存原始内容、解析结果、证据和版本；
- 失败任务可以重试；
- 重复内容可以被识别；
- ready 状态 JD 可以用于匹配。

## 22.2 匹配分析

- 用户可以选择指定简历版本和 JD 版本；
- 系统可以输出总分和维度分；
- 系统可以展示匹配证据；
- 系统可以区分真实缺口、表达缺口和证据不足；
- 系统可以识别硬性风险；
- 报告可以创建模拟面试。

## 22.3 面试创建

- 用户可以选择面试场景、时长和难度；
- 系统可以生成 Interview Plan；
- 计划包含阶段、问题、能力项和风险验证；
- 用户确认计划后才进入面试；
- 创建和开始动作相互独立。

## 22.4 面试运行

- 系统按照阶段执行面试；
- 支持动态追问；
- 支持暂停和恢复；
- 每个问题、回答、评分均独立保存；
- 面试可以正常结束；
- 异常后可以恢复；
- 不出现无限追问；
- 系统可以生成最终报告。

## 22.5 面试报告

- 包含总体评分；
- 包含能力维度；
- 包含高表现问题；
- 包含薄弱问题；
- 包含 JD 覆盖情况；
- 包含岗位适配建议；
- 包含下一步行动建议。

---

# 23. 推荐开发顺序

建议按照以下顺序推进：

```text
1. JD 统一数据结构
2. JD 导入、解析、确认和版本管理
3. 简历与 JD 匹配报告结构
4. 匹配规则与证据模型
5. Interview Scenario
6. Interview Plan
7. Interview Session 状态机
8. 问题覆盖矩阵
9. Answer Evaluator
10. 动态追问
11. 面试报告
12. RAG 增强
13. Agent Eval
14. 语音与其他高级场景
```

---

# 24. 最终结论

本产品不应被设计成一条简单的：

```text
上传 JD → 让大模型开始提问
```

而应当建立为一套可追溯、可评测、可扩展的结构化面试系统：

```text
JD 资料库
→ 简历与 JD 匹配
→ 面试场景
→ 面试方案
→ 面试状态机
→ 动态追问
→ 单题评估
→ 综合报告
→ 学习与求职计划
```

在正式增加复杂 RAG 和 Multi-Agent 之前，应优先完成以下五个核心基础：

1. JD 统一数据结构；
2. 匹配报告结构；
3. Interview Scenario；
4. Interview Plan；
5. Interview Session 状态机。

完成这五部分后，后续的检索、题库、评分器、语音面试和多 Agent 能力都可以稳定接入。
