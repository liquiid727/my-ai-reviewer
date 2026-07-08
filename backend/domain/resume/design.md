Resume Domain 建模
Resume：聚合根，代表一份简历，不等于文件本身
ResumeDocument：原始文件信息，比如 PDF/DOCX、存储路径、hash、页数
ResumeParsedText：解析出的原始文本、分段文本、解析器版本
CandidateProfile：标准化后的候选人画像，是后续面试 Agent 的主要输入
ResumeSection：简历分区，比如基础信息、教育经历、工作经历、项目经历、技能、证书
ResumeFact：从简历里抽取出的事实，带 confidence、source_text、page、section
ResumeClassification：分类结果，比如候选人方向、技术栈、年限、岗位匹配标签
固定信息可以标准化
简历里比较稳定的内容可以建成明确字段：
CandidateProfile
├── identity
│   ├── name
│   ├── email
│   ├── phone
│   ├── location
│   └── links
├── education[]
│   ├── school
│   ├── degree
│   ├── major
│   ├── start_date
│   └── end_date
├── work_experiences[]
│   ├── company
│   ├── title
│   ├── start_date
│   ├── end_date
│   ├── responsibilities[]
│   └── achievements[]
├── projects[]
│   ├── name
│   ├── role
│   ├── tech_stack[]
│   ├── background
│   ├── responsibility
│   ├── highlights[]
│   └── metrics[]
├── skills[]
│   ├── name
│   ├── category
│   ├── evidence
│   └── confidence
└── certificates[]
重点是 Fact + Evidence
不要只存最终结果，比如：
{
  "skill": "Redis",
  "category": "backend_cache",
  "evidence": "负责 Redis Cluster 缓存架构设计",
  "source_section": "project_experience",
  "confidence": 0.92
}
这样后面 Evaluation / Question Agent 才能知道：这个技能是候选人明确写过的，还是模型推断出来的。
Resume 重点分类
建议至少分这几类：
基础信息：姓名、联系方式、城市、链接
教育背景：学校、专业、学历、时间
工作经历：公司、职位、时间、职责、成果
项目经历：项目名、业务背景、技术栈、个人职责、难点、指标
技能栈：语言、框架、中间件、数据库、云原生、AI/LLM、工具
能力标签：后端、前端、算法、架构、运维、数据、AI 应用
面试线索：值得追问的点、可疑夸大点、强相关经历、弱项空白
岗位匹配：JD 技能命中、缺失项、风险点、推荐面试阶段侧重
数据库上不要全拍平成字段
推荐组合：
resumes：简历主表，状态、用户、文件、解析版本
resume_sections：分段结果
resume_facts：结构化事实，适合追溯和复核
candidate_profiles：标准化候选人画像，JSONB 存完整快照
resume_skill_tags：技能标签和证据
resume_project_profiles：项目经历的结构化结果
这样既能查固定字段，也不会被简历格式变化卡死。
后续实现顺序建议
先定义 Resume 聚合和 CandidateProfile 标准 schema  
再做 parser，把 PDF/DOCX 变成 ResumeParsedText
然后做 extractor，把文本变成 ResumeFact
最后做 classifier，把 facts 归纳成技能画像、项目画像、面试追问点
resume 这一块的目标不是“解析简历”，而是生成一个可被面试系统消费的候选人画像。这个画像要足够稳定，才能支撑后面的出题、追问、评分和报告。
