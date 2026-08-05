JD 资料库 → 简历与 JD 匹配 → 面试方案创建 → 模拟面试执行与报告

我们的这个产品链路应该拆分成以下四个相对独立的模版

（方便后续做RAG Agent 语音面试 还是多轮面试都不会把业务逻辑揉成一团）

 4份PRD：

 PRD 1：JD 导入与职位资料库
 
 负责解决：
 
 JD 从哪里来
 如何提取
 如何结构化
 如何校正
 如何存储和版本管理

 PRD 2：简历与 JD 匹配评估
 
 负责解决：
 
 用户选择哪份简历和哪份 JD
 匹配度如何计算
 为什么匹配或不匹配
 哪些能力需要补足
 是否适合进入模拟面试

 PRD 3：模拟面试创建与场景配置
 
 负责解决：
 
 模拟哪一轮面试
 面试官是什么角色
 面试重点是什么
 时长、难度、问题数量如何配置
 如何生成一份可执行的面试方案
 PRD 4：模拟面试运行与报告
 
 负责解决：
 
 如何提问
 如何追问
 如何评分
 如何暂停、恢复、结束
 如何生成报告和后续学习计划

 注意：
 创建面试和开始面试必须是两个动作。
 
 创建面试时先生成一份 Interview Plan；用户确认之后，才正式进入 Interview Session。
 
 否则 Agent 一进来就开始自由发挥，问题覆盖、时长、难度和评分标准都会不可控

 三、JD 导入 PRD
 3.1 功能目标
 
 用户可以通过多种方式导入职位描述，平台完成：
 
 原始内容获取
 文本标准化
 JD 结构化解析
 证据定位
 用户校正
 版本化存储

 3.2 支持的导入方式
 
 MVP 建议支持以下 5 种：
 
 导入方式	使用场景	处理方式
 粘贴文本	用户复制招聘网站内容	直接清洗和解析
 上传文件	PDF、DOCX、TXT、MD	文件解析后识别
 上传图片	招聘软件截图、聊天截图	OCR 后解析
 输入链接	官网、招聘平台公开页面	抓取页面正文
 手动创建	内容很少或需要自己补充	表单填写
 
 链接导入不要一开始承诺所有招聘平台都能解析。
 
 建议产品文案写成：
 
 支持公开可访问的职位链接；部分需要登录或存在访问限制的网站可能无法自动获取。
 
 后续可以通过浏览器插件或剪贴板助手解决登录态页面采集。

 3.3 导入交互
 
 点击“导入 JD”后进入一个分步弹窗或独立页面。
 
 第一步：选择导入方式
 粘贴文本
 上传文件
 上传图片
 输入链接
 手动填写
 第二步：补充来源信息
 
 自动获取不到时允许用户填写：
 
 公司名称
 岗位名称
 来源平台
 原始链接
 工作地点
 备注
 标签
 第三步：系统解析
 
 展示处理状态：
 
 正在读取内容
 正在清理职位文本
 正在识别岗位要求
 正在生成结构化职位信息
 第四步：确认识别结果
 
 用户看到结构化内容，并可修改：
 
 岗位名称
 公司名称
 岗位职责
 必须技能
 优先技能
 工作年限
 学历要求
 职级
 薪资范围
 工作地点
 行业和业务方向
 加分项
 其他要求
 第五步：保存
 
 保存后进入 JD 详情页，而不是直接开始面试。
 
 详情页提供：
 
 查看原始内容
 查看结构化信息
 修改识别结果
 重新解析
 选择简历进行匹配
 创建模拟面试

 四、JD 标准数据结构
 
 你前面已经做了 required skills、preferred skills、职责、职级和岗位元数据，这里可以进一步统一成一个稳定的数据合同。
 举例：
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
         "confidence": 0.98
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

 五、JD 处理状态机
 
 JD 不应该只有“成功”和“失败”。
 
 建议设计为：
 
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
 
 异常状态：
 
 extract_failed
 parse_failed
 unsupported
 duplicate
 archived
 
 其中：
 
 needs_review：已经解析，但置信度较低或存在字段冲突
 confirmed：用户已经确认结构化结果
 ready：可以用于匹配和面试
 duplicate：检测到相同链接、文件哈希或高度相似内容
 
 只有 ready 状态的 JD，默认允许进入匹配和面试。
 
 六、简历与 JD 匹配 PRD
 6.1 产品入口
 
 建议提供三个入口：
 
 JD 详情页：匹配简历
 简历详情页：匹配职位
 独立匹配中心：创建匹配分析
 
 三个入口最终进入同一个页面：
 
 选择简历版本
 +
 选择 JD 版本
 +
 开始匹配分析
 
 一定要选择“版本”，而不只是选择 resume_id 和 jd_id。
 
 否则用户修改了简历或 JD 后，历史匹配报告会发生含义漂移。
 
 6.2 匹配评分结构
 
 不建议只输出一个“匹配度 82%”。
 
 应该输出“总分 + 维度 + 证据 + 缺口”。
 
 可以采用下面的评分结构：
 
 维度	建议权重
 必须技能匹配	25
 工作经验与年限	15
 项目经历匹配	20
 岗位职责相关度	15
 技术栈与工具	10
 行业和业务经验	5
 学历、地点等基础要求	5
 优先项与加分项	5
 
 总分 100。
 
 需要增加一些强约束规则，例如：
 
 缺失核心必须技能：
 总分上限为 75
 
 工作年限严重不足：
 总分上限为 70
 
 完全不满足明确学历硬性要求：
 标记为风险，但是否封顶由岗位类型决定
 
 否则模型可能因为“语义看起来很相关”，给出一个虚高分。
 
 6.3 匹配技术方案
 
 建议使用混合评分，而不是全部交给 LLM：
 
 规则匹配
     +
 技能标准化
     +
 Embedding 语义匹配
     +
 LLM 证据判断
     +
 加权评分器
 
 具体职责：
 
 规则引擎：工作年限、学历、地点、证书等明确条件
 技能词典：Go/Golang、PostgreSQL/Postgres 等同义词
 Embedding：项目描述和岗位职责的语义相关度
 LLM：判断项目经历是否真的能证明某项能力
 评分器：统一聚合和封顶规则
 
 不要让 LLM 直接看完简历和 JD，随口输出“匹配度 86%”。
 
 6.4 匹配报告页面
 
 建议页面分成 5 个区域：
 
 区域一：总体结论
 综合匹配度：78
 推荐程度：值得投递，但需要针对性优化
 区域二：能力雷达或维度评分
 技能
 项目
 经验
 业务
 基础条件
 加分项
 区域三：已匹配能力
 
 每项展示：
 
 JD 要求
 简历证据
 匹配结论
 置信度
 区域四：能力缺口
 
 区分：
 
 真实能力缺口
 简历表达缺口
 缺少证据
 硬性条件风险
 
 这个区分非常重要。
 
 例如用户可能真的会 Redis，只是简历里没写。系统不应该直接断言“用户不会 Redis”，而应该说：
 
 简历中未找到可以证明 Redis 实践经验的内容。
 
 区域五：下一步行动
 优化当前简历
 生成针对性简历
 创建模拟面试
 生成学习计划
 添加到求职计划
 
 这正好把你的几个产品模块串起来。
 
 七、模拟面试创建 PRD
 
 这是你现在最需要补的一层。
 
 7.1 创建面试需要的输入
 
 用户点击“创建模拟面试”后，应当确认以下内容：
 
 基础材料
 简历版本
 JD 版本
 匹配报告，可选但建议默认使用
 面试场景
 综合模拟面试
 HR 初筛
 技术一面
 项目深挖
 系统设计
 行为面试
 主管面试
 自定义专项面试
 面试配置
 面试时长：15 / 30 / 45 / 60 分钟
 难度：基础 / 标准 / 挑战
 模式：文字 / 语音
 语言：中文 / 英文
 追问强度：温和 / 标准 / 深挖
 是否提供即时提示
 是否允许跳过问题
 是否展示阶段进度
 
 MVP 不要开放太多复杂选项。
 
 建议首版只提供：
 
 面试场景
 面试时长
 难度
 文字或语音
 
 其他参数使用场景模板默认值。
 
 八、面试场景不是一段 Prompt
 
 这里是整个设计里最关键的一点。
 
 一个面试场景应该是一份结构化配置，而不是：
 
 你现在是一个严格的技术面试官……
 
 建议定义 InterviewScenario：
 
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
 
 以后增加新的面试场景，本质上就是增加新的模板，而不是重写 Agent。
 
 九、面试方案 Interview Plan
 
 创建面试后，系统先生成一份 Interview Plan。
 
 例如：
 
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
 
 每个计划问题应当包含：
 
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
   "follow_up_candidates": [],
   "scoring_rubric": {}
 }
 
 用户不一定要看到所有评分规则，但系统内部必须有。
 
 十、模拟面试运行流程
 
 建议按照下面的阶段执行：
 
 阶段 1：面试准备
 检查简历和 JD 是否可用
 构建会话上下文
 载入场景模板
 生成面试计划
 初始化评分标准
 阶段 2：开场
 说明面试场景和预计时长
 提醒用户可以暂停或结束
 进行自我介绍问题
 阶段 3：基础验证
 
 围绕：
 
 求职动机
 核心经历
 当前职责
 与岗位的关联
 阶段 4：项目深挖
 
 遵循一条基本追问链：
 
 你做了什么
 → 为什么这么做
 → 具体如何实现
 → 遇到了什么问题
 → 如何验证结果
 → 有没有其他方案
 阶段 5：JD 专项考察
 
 优先覆盖：
 
 JD 的必须技能
 匹配报告中的高风险项
 简历中声称但证据不足的能力
 高价值项目经历
 阶段 6：综合题或场景题
 
 例如：
 
 系统设计
 故障排查
 技术选型
 业务场景
 协作冲突
 阶段 7：候选人反问
 
 允许用户进行 1～3 个反问。
 
 面试官可以评价反问质量，但不应虚构具体公司内部信息。
 
 阶段 8：结束和报告生成
 结束面试会话
 异步聚合评分
 生成报告
 生成建议和练习计划
 十一、面试运行状态机
 
 建议使用如下状态：
 
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
 
 其他状态：
 
 cancelled
 failed
 expired
 terminated
 
 问题状态也要独立记录：
 
 planned
 asked
 answered
 evaluated
 followed_up
 skipped
 abandoned
 
 千万不要只把整个面试保存为一大段聊天记录。
 
 否则后面无法：
 
 恢复会话
 回放问题
 分析覆盖率
 重跑评分
 对比不同模型
 建立 Agent Eval
 十二、Agent 和 RAG 应该如何分工
 
 你后续确实需要 RAG 和 Agent，但不要把所有事情交给一个“面试官 Agent”。
 
 建议拆成以下职责。
 
 1. Interview Orchestrator
 
 负责：
 
 控制阶段
 控制时间
 选择下一道题
 判断是否进入追问
 判断是否结束
 
 这部分适合使用 LangGraph 状态机。
 
 2. Interviewer
 
 负责：
 
 用自然语言提问
 根据场景调整口吻
 根据答案生成追问
 保持对话连贯
 3. Answer Evaluator
 
 负责：
 
 对单次回答评分
 提取关键观点
 判断回答是否完整
 判断是否存在矛盾
 给出追问信号
 
 Evaluator 最好和 Interviewer 逻辑分开。
 
 否则“既提问又立即给自己提的问题打分”，容易出现评分偏差和上下文污染。
 
 4. Retrieval Layer
 
 负责检索：
 
 当前简历事实
 JD 要求
 匹配报告
 历史回答
 问题库
 评分标准
 行业知识库
 5. Report Generator
 
 负责：
 
 汇总单题评分
 计算能力维度
 输出优势和风险
 生成改进建议
 生成学习和练习计划
 
 首版不必真的部署成 5 个独立 Agent。
 
 可以是一套 LangGraph 工作流，内部使用不同节点和不同 Prompt：
 
 Orchestrator Node
 Interviewer Node
 Evaluator Node
 Retriever Node
 Report Node
 
 这比一开始就上复杂 Multi-Agent 稳定得多。
 
 十三、RAG 内容应该分层
 
 你的面试 RAG 可以分成三层。
 
 第一层：用户私有上下文
 简历事实
 项目经历
 技能
 JD 内容
 匹配报告
 当前会话回答
 
 这是每次面试必须加载的。
 
 第二层：面试能力库
 岗位能力模型
 面试题库
 追问模板
 评分 Rubric
 优秀回答信号
 常见风险信号
 
 这是平台公共知识。
 
 第三层：行业和公司资料
 公司公开介绍
 产品信息
 行业术语
 技术栈信息
 公开面试经验
 
 这部分应当标记来源和有效时间，且不能把网友面经当作官方事实。
 
 MVP 可以先不做第三层，优先把前两层跑通。
 
 十四、需要建立“问题覆盖矩阵”
 
 每场面试都应当有一张内部覆盖矩阵：
 
 能力项	来源	重要性	是否已提问	得分	证据充分度
 Go 并发	JD 必须技能	高	是	4	高
 Agent 状态机	JD 职责	高	是	3	中
 RAG 评测	匹配缺口	高	是	2	低
 项目负责程度	简历项目	中	是	4	高
 沟通表达	通用能力	中	是	3	中
 
 Orchestrator 根据这张表决定下一题，而不是完全依赖大模型临场发挥。
 
 十五、面试报告结构
 
 最终报告建议包含：
 
 1. 总体结果
 综合表现：72/100
 岗位适配建议：可以继续准备后投递
 模拟轮次：技术一面
 2. 能力维度
 技术正确性
 技术深度
 项目真实性
 问题分析
 方案权衡
 表达结构
 岗位适配度
 3. 高表现问题
 
 展示：
 
 问题
 用户回答摘要
 优秀点
 对应能力证据
 4. 薄弱问题
 
 展示：
 
 问题
 回答缺口
 为什么不足
 推荐答题结构
 建议练习内容
 5. JD 覆盖情况
 已验证必须能力：6/8
 表现良好：3
 基本满足：2
 存在风险：1
 尚未验证：2
 6. 下一步计划
 修改简历
 重新练习某类问题
 学习指定知识
 再进行一次专项面试
 加入求职 Todo
 
 这就能和你的“JD 学习路线 + Todo 计划”自然打通。
 
 十六、核心数据库实体
 
 你现有简历和面试表可以继续使用，但建议补齐以下实体。
 
 JD 相关
 job_descriptions
 job_description_versions
 job_description_sources
 job_description_parse_runs
 job_description_fields
 job_description_evidence
 匹配相关
 resume_jd_matches
 match_dimensions
 match_requirements
 match_evidence
 match_recommendations
 面试创建相关
 interview_scenarios
 interview_templates
 interview_plans
 interview_plan_stages
 interview_plan_questions
 面试运行相关
 interview_sessions
 interview_questions
 interview_answers
 answer_evaluations
 interview_events
 interview_reports
 interview_report_dimensions
 
 其中 interview_events 非常重要，可以记录：
 
 session.created
 plan.generated
 session.started
 question.asked
 answer.submitted
 answer.evaluated
 followup.generated
 session.paused
 session.resumed
 session.completed
 report.generated
 
 以后做问题回放、故障恢复、Agent Eval、成本统计都会依赖这张事件表。

 十七、你当前页面建议怎么调整
 
 你现在这个页面更像“JD 空列表页”，方向没问题，但缺少后续动作表达。
 
 空状态
 
 现在的：
 
 导入一份 JD 后即可将岗位与简历进行匹配。
 
 可以改成：
 
 导入职位描述，系统会自动识别岗位职责、技能要求和面试重点。
 
 按钮仍然是：
 
 导入 JD
 有数据后的 JD 列表
 
 每一条 JD 建议展示：
 
 AI Agent 开发工程师
 某某科技 · 杭州 · 3-5 年
 
 必须技能：Python / RAG / Agent / LangGraph
 来源：官方网站
 状态：已确认
 更新时间：2 小时前
 
 右侧操作：
 
 查看详情
 匹配简历
 创建面试
 更多
 页面顶部
 
 保留：
 
 导入 JD
 
 增加次级入口：
 
 创建匹配分析
 
 不过“创建面试”不建议直接固定在页面顶部。
 
 因为创建面试必须明确：
 
 哪份 JD
 哪份简历
 哪种场景
 
 应该从 JD 行、简历行或匹配报告进入。
