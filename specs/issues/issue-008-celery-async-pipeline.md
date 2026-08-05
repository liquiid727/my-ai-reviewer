# Celery Async Pipeline Orchestration

## Description

实现 Celery 异步任务链，编排 text_extract → llm_parse → classify → evaluate 四步管道。提供状态查询和手动重试 API。

PRD Reference: US-007
SPEC Reference: Section 5.1 (pipeline), 6.3

## Acceptance Criteria

- [ ] `backend/tasks/resume_tasks.py`：定义 Celery 任务链
- [ ] 文件上传成功后自动触发 `process_resume_pipeline` 异步任务
- [ ] 任务链：text_extract → llm_parse → classify → evaluate，每步更新 resume status
- [ ] `GET /api/v1/resume/{resume_id}/status` 返回：status, current_step, completed_steps, error
- [ ] `GET /api/v1/resume/{resume_id}` 返回当前已完成的解析结果（部分结果可查看）
- [ ] `POST /api/v1/resume/{resume_id}/retry` 从失败步骤重新执行
- [ ] 任一步骤失败 → status 标记 `failed`，记录失败步骤和错误信息
- [ ] 任务超时配置：text_extract 30s, llm_parse 120s, classify 30s, evaluate 120s
- [ ] LLM 调用失败自动重试（max_retries=2, retry_delay=30s）
- [ ] API 响应 schemas 定义（ResumeStatusResponse, ResumeDetailResponse）
- [ ] `GET /api/v1/resume/{resume_id}/evaluation` 返回评估报告（EvaluationResponse）
- [ ] Typecheck 通过

## Dependencies

Issue #4, #5, #6, #7

## Type

backend

## Priority

P0
