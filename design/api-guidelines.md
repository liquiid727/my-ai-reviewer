# API Guidelines

## 核心业务流程

```text
创建面试
  ↓
上传简历
  ↓
输入岗位 JD
  ↓
简历分析（Resume Agent）
  ↓
JD 分析
  ↓
生成面试计划
  ↓
阶段提问（Question Agent）
  ↓
候选人回答
  ↓
AI 评分（Evaluation Agent）
  ↓
AI 追问（Followup Agent）
  ↓
生成最终报告（Report Agent）
  ↓
结束面试
```

---

## REST 接口规范

### URL 命名
```text
/api/{resource}/{action}

示例：
POST   /api/resume/upload
POST   /api/interview/create
GET    /api/interview/{id}
POST   /api/interview/{id}/start
POST   /api/interview/{id}/answer
GET    /api/interview/{id}/report
```

### 响应格式
```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### 错误码
```text
0     成功
1001  参数错误
1002  资源不存在
1003  状态错误（如面试已结束）
5001  LLM 调用失败
5002  Agent 执行超时
```

---

## 核心接口定义

### 简历服务

```http
POST /api/resume/upload
Content-Type: multipart/form-data

Body:
  file: PDF/DOCX
  interview_id: string (optional)

Response:
{
  "resume_id": "xxx",
  "parsed": {
    "skills": [],
    "projects": []
  }
}
```

---

### 面试服务

```http
POST /api/interview/create
Content-Type: application/json

Body:
{
  "resume_id": "xxx",
  "jd_text": "...",
  "stages": ["resume", "basic", "project", "system_design"]
}

Response:
{
  "interview_id": "xxx",
  "status": "pending"
}
```

---

### 问答流程

```http
POST /api/interview/{id}/start
→ 触发 LangGraph Workflow，返回第一个问题

POST /api/interview/{id}/answer
Body: { "answer": "..." }
→ 评分 + 返回下一个问题或追问

GET /api/interview/{id}/report
→ 返回最终报告（面试结束后可用）
```

---

## 异步任务

耗时操作（简历解析、报告生成）走 Celery 异步任务：

```http
POST /api/resume/upload
→ 返回 task_id

GET /api/tasks/{task_id}
→ 查询任务状态和结果
```
