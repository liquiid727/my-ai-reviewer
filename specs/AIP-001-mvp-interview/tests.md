# AIP-001 Tests

## 验收测试（手动）

### TC-001 简历上传
```
步骤：
  1. 准备一份 PDF 简历（含 Go、Redis、PostgreSQL 技能）
  2. POST /api/v1/resume/upload

期望：
  - 状态码 200
  - 返回 resume_id
  - skills 列表包含简历中的技术栈
  - projects 列表包含项目名称
```

### TC-002 创建面试
```
步骤：
  1. 使用 TC-001 的 resume_id
  2. POST /api/v1/interview/create，附带 jd_text 和 question_count=5

期望：
  - 状态码 200
  - 返回 interview_id
  - status = "pending"
```

### TC-003 开始面试
```
步骤：
  1. POST /api/v1/interview/{id}/start

期望：
  - 状态码 200
  - 返回一个与简历/JD 相关的面试问题
  - 数据库中 interview.status 更新为 in_progress
```

### TC-004 完整问答循环
```
步骤：
  1. 连续 POST /api/v1/interview/{id}/answer 5 次，每次给出不同答案

期望：
  - 每次返回 score (0-100) 和 feedback
  - 前 4 次 is_finished=false，next_question 非空
  - 第 5 次 is_finished=true，next_question=null
```

### TC-005 获取报告
```
步骤：
  1. TC-004 完成后
  2. GET /api/v1/interview/{id}/report

期望：
  - 状态码 200
  - overall_score 在 0-100 之间
  - summary 非空
  - strengths 和 improvements 各至少 1 条
  - 所有数据已持久化（重启后仍可查询）
```

---

## 单元测试

### Resume Agent
```python
def test_resume_agent_extracts_skills():
    # mock LLM response
    # 验证 skills 和 projects 结构正确
```

### Evaluation Agent
```python
def test_evaluation_agent_returns_score():
    # 验证 score 在 0-100 范围
    # 验证 feedback 非空
```

### LangGraph Workflow
```python
async def test_interview_graph_full_flow():
    # mock 所有 Agent
    # 验证 State 流转正确
    # 验证 END 节点能到达
```

---

## 边界情况

| 场景 | 期望行为 |
|---|---|
| 上传非 PDF/DOCX 文件 | 400 错误，提示不支持的格式 |
| 面试不存在 | 404 错误 |
| 面试已结束再答题 | 400 错误，提示面试已完成 |
| LLM 调用超时 | 500 错误，提示服务暂时不可用 |
| 简历文本为空 | 解析成功但 skills 返回空列表 |
