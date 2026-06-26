# Domain

## DDD 分层结构

```text
backend/
├── domain/
│   ├── interview/
│   ├── resume/
│   ├── question/
│   ├── evaluation/
│   └── report/
│
├── application/
│   ├── interview_service/
│   ├── resume_service/
│   ├── question_service/
│   ├── evaluation_service/
│   └── report_service/
│
└── infrastructure/
    ├── db/
    ├── cache/
    ├── vector/
    ├── storage/
    └── llm/
```

---

## 面试阶段

| 阶段 | 说明 |
|---|---|
| Introduction | 开场介绍 |
| Resume | 简历追问 |
| Basic | 技术基础 |
| Project | 项目经验 |
| System Design | 系统设计 |
| Behavior | 行为面试 |
| Summary | 总结反馈 |

---

## LangGraph Workflow

### InterviewState

```python
class InterviewState(TypedDict):
    interview_id: str
    user_id: str
    stage: str
    resume_summary: str
    jd_summary: str
    current_question: str
    current_answer: str
    score: float
    history: list
```

### Graph 流程

```text
START
  ↓
Analyze Resume
  ↓
Analyze JD
  ↓
Build Plan
  ↓
Stage Router
  ↓
Generate Question
  ↓
Wait Answer
  ↓
Evaluate
  ↓
Need Followup?
  ├── Yes → Followup → (回到 Generate Question)
  └── No  ↓
Next Stage
  ↓
Generate Report
  ↓
END
```

---

## Agent 设计

### Resume Agent
**职责**：解析简历、提取技能、提取项目、生成候选人画像

**输出**：
```json
{
  "skills": ["Go", "Redis", "Kubernetes"],
  "projects": [
    {
      "name": "...",
      "tech": [...],
      "role": "..."
    }
  ]
}
```

---

### Question Agent
**职责**：生成面试题、控制难度、避免重复问题

**输入**：Resume + JD + Interview History

**约束**：
- 根据候选人技能栈定向出题
- 按当前 Stage 控制题型
- 记录已出题目，避免重复

---

### Evaluation Agent
**职责**：回答评分、输出评价

**评分维度**：
- 技术正确性（Technical Correctness）
- 工程深度（Engineering Depth）
- 表达能力（Communication）
- 逻辑能力（Problem Solving）

**输出**：
```json
{
  "technical": 80,
  "engineering": 90,
  "architecture": 75,
  "communication": 88,
  "summary": "..."
}
```

---

### Followup Agent
**职责**：根据候选人回答生成深度追问

**示例追问**：
```text
你提到用了 Redis Cluster，为什么这样设计？
节点故障时如何处理？
为什么不选择 Codis？
```

---

### Report Agent
**职责**：生成最终面试报告

**报告内容**：
- 技术能力评估
- 项目能力评估
- 架构能力评估
- 综合评价
- 改进建议
