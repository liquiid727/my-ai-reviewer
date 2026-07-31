# [姓名]

- 手机：[手机号码]
- 邮箱：[邮箱地址]
- 微信：[微信号]
- GitHub：[GitHub 地址]
- 技术博客：[博客地址]
- 所在城市：[当前城市]
- 目标城市：杭州
- 工作年限：3 年+

## 求职意向

- 目标岗位：AI 应用开发工程师 / AI 全栈应用工程师
- 期望方向：企业级 AI 应用、RAG 知识库、AI Gateway、智能客服、工作流自动化
- 到岗时间：[到岗时间]

## 个人简介

拥有 3 年以上 Go 后端与平台工程经验，具备复杂业务系统、分布式服务、资源调度、支付计费和可观测性建设经验。当前重点转向 AI 应用开发，围绕 LLM API、Structured Output、Function Calling、MCP、RAG、Workflow、Agent、上下文工程和评测体系进行系统学习与项目实践。

能够将 AI 能力接入现有业务系统，完成从需求分析、模型接入、知识库检索、工具调用、服务编排到部署监控的完整链路。熟悉 Go 服务端开发，同时具备 Python、FastAPI、React 和 AI Coding 工具链实践经验，适合承担“后端工程能力 + AI 产品落地”的复合型岗位。

## 核心技能

### AI 应用开发

- LLM API：OpenAI-compatible API、流式输出、Structured Output、Function Calling、Prompt Engineering
- RAG：文档解析、Chunking、Embedding、Dense / Sparse / Hybrid Search、Rerank、知识库更新
- Agent 与 Workflow：LangGraph、LangChain、Dify、MCP、Tool Calling、Memory、Planning、Human-in-the-loop
- AI 工程化：模型路由、上下文压缩、Token 成本控制、Tracing、Eval、Guardrails、Retry、Fallback
- AI 开发工具：Claude Code、Codex CLI / App、Qoder、AGENTS.md、Spec 驱动开发

### 后端与平台

- 编程语言：Go、Python、SQL、JavaScript / TypeScript
- Web 框架：Gin、FastAPI、React、Vite
- 数据存储：PostgreSQL、MySQL、Redis、Milvus
- 基础设施：Docker、Kubernetes、Nginx、Linux、Git
- 可观测性：Prometheus、Grafana、Loki、Tempo、Zap JSON Logging、Trace ID
- 工程能力：微服务、RESTful API、SSE、幂等设计、分布式锁、状态机、异步任务、限流与重试

## 工作经历

### 某科技公司｜Go 后端开发工程师

**2023.01 - 至今**

- 负责云游戏后端、订阅计费、资源调度、支付接入和管理平台等核心模块的设计与开发。
- 使用 Go、Gin、PostgreSQL、Redis 构建 API 服务、资源连接服务、节点管理服务和图片服务。
- 设计用户排队、资源分配、会话续租和回收状态机，处理并发分配、资源锁、租约与异常恢复。
- 建设统一日志和可观测性链路，接入 Prometheus、Grafana、Loki、Tempo，并通过 trace_id 和 request_id 串联请求。
- 参与支付宝支付、钱包、时长计费、权益卡券、VIP 权益和订单幂等机制建设。
- 推动使用 PRD、Spec、AGENTS.md、测试规范和 AI Coding Agent 改造研发流程，提高需求到代码交付的一致性。

### 众安在线 / 暖哇科技｜大数据开发

**2022.05 - 2022.10**

- 参与数据处理、任务开发和业务数据分析相关工作。
- 使用 SQL、数据处理工具和服务端技术完成数据清洗、任务维护及问题排查。
- 积累了数据链路、业务指标和工程协作方面的基础经验。

## 项目经历

### 企业级 AI Gateway 与模型服务平台

**角色：核心开发 / 架构设计｜项目类型：个人项目 / 二次开发**

**技术栈：Go、NewAPI、PostgreSQL、Redis、OpenAI-compatible API、Docker、Prometheus**

- 基于 NewAPI 进行二次开发，面向企业内部统一管理 OpenAI、Claude、Gemini、DeepSeek、Qwen、Kimi 等模型渠道。
- 设计租户、预算、模型权限、渠道账号池、倍率计费、成本统计和请求审计能力。
- 规划质量优先、成本优先和自动降级等路由策略，并支持模型不可用时的 fallback。
- 设计模型能力矩阵和评测数据结构，为 Coding、RAG、Agent、长上下文等场景选择合适模型。
- 建设统一调用日志、Token 用量、错误率、延迟和渠道健康度监控，为企业 AI 应用提供稳定底座。

### 企业知识库与智能客服应用

**角色：AI 应用开发｜项目类型：个人项目 / 作品集**

**技术栈：Python、FastAPI、LangGraph、Dify、Milvus、PostgreSQL、Redis、RAG、MCP**

- 面向 QQ、微信、钉钉和飞书等渠道设计统一智能客服接入层。
- 构建文档解析、切分、Embedding、混合检索、Rerank 和答案生成链路。
- 使用工作流区分 FAQ、知识库问答、业务查询、人工客服转接和高风险问题。
- 通过 Function Calling / MCP 调用订单、用户、权益和工单等内部服务。
- 设计引用来源、置信度、拒答、敏感信息过滤和人工兜底机制，降低错误回答风险。
- 规划 Golden Dataset、命中率、答案正确率、召回率和人工接管率等评测指标。

### 云游戏资源调度与会话平台

**角色：Go 后端核心开发｜项目类型：工作项目**

**技术栈：Go、Gin、PostgreSQL 16、Redis、SSE、Docker、Nginx、Prometheus**

- 拆分 api-server、connection-plane、fleet-daemon 和 image-service 等服务，支撑用户登录、排队、资源分配和游戏会话。
- 设计 connecting、active、hold、grace、stopping、stopped 等会话状态，以及 available、in_use、recycling、quarantine 等资源状态。
- 基于 Redis 构建分布式锁、实例所有权、会话租约和资源映射，降低并发分配冲突。
- 实现用户排队优先级和会员配额策略，支持普通用户、VIP、SVIP 以及资源借用规则。
- 使用 SSE 推送 queue.update、assigned、time.balance_updated、expiring 等实时事件。
- 建设 promo、free、member、paid、offpeak 等时长桶及可配置结算周期，保证扣减幂等和流水可追踪。

### SpecOS AI 研发工作流

**角色：产品设计 / 全栈开发｜项目类型：个人项目 / 研发中**

**技术栈：Go、Python、React、CLI、Agent、Spec、Workflow**

- 设计从 PRD、Spec、Architecture、Task、Code、Test 到 Deploy 的规范驱动研发流程。
- 通过不同 Agent 路由规划、后端开发、前端开发、测试和代码审查任务。
- 规划 CLI Adapter 和 GUI 工作台，使 Codex、Claude Code、GLM、Kimi 等 CLI 能在统一界面中切换。
- 设计 Session Manager、Runtime Orchestrator、上下文管理和执行记录，保留人工确认节点。
- 将性能测试、场景测试、E2E、契约测试和 QA Gate 纳入 Spec-Test 体系。

## 教育经历

### [本科院校]｜计算机相关专业｜本科

**[入学时间] - [毕业时间]**

- 学业成绩：专业前 30%
- 英语水平：CET-6
- 主要课程：数据结构、计算机网络、操作系统、数据库、软件工程

## 论文与其他经历

### 《基于 OpenPose 的动作序列相似度计算算法》

**2021.05 - 2021.10**

- 参与人体动作识别与动作序列相似度算法研究。
- 论文曾获得 200+ 引用与下载记录。
- 涉及 OpenPose、姿态关键点、时序数据处理和相似度计算。

## 自我评价

- 具备较强的后端工程基础，能够独立完成复杂业务模块的分析、设计、开发和上线。
- 注重 AI 应用的可控性、可评测性和工程边界，不将模型能力等同于系统能力。
- 善于通过 Spec、测试、Tracing 和人工确认机制约束 AI 生成结果。
- 持续学习 Agent、RAG、AI Gateway 和企业级 AI 平台架构，能够快速完成业务原型和工程落地。
