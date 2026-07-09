# AI Resume Multi-Dimensional Evaluation

## Description

实现基于 LLM 的简历多维度评估，模拟资深技术面试官视角。输出综合评分、8 维度评分、优势分析、风险分析、面试建议和综合评价。

PRD Reference: US-006
SPEC Reference: Section 5.5, 5.7

## Acceptance Criteria

- [ ] `backend/infrastructure/evaluators/base.py`：ResumeEvaluator ABC
- [ ] `backend/infrastructure/evaluators/llm_evaluator.py`：调用 LLMGateway 进行评估
- [ ] `backend/infrastructure/llm/prompts/evaluation.py`：评估 system prompt（模拟 10 年+技术面试官）
- [ ] 综合评分：Overall Score (0-100)
- [ ] 8 维度评分（每项 0-100 + reason + evidence）：技术能力、项目质量、工程能力、架构能力、业务复杂度、影响力、成长性、AI 能力
- [ ] 优势分析：3-5 条，每条附带 evidence
- [ ] 风险分析：每条附带 evidence + severity（high/medium/low）
- [ ] 面试建议：worth_asking, suspicious, verify_direction, skip 四个列表
- [ ] 综合评价 Summary：2-3 句话
- [ ] 评估结果存入 `resume_evaluations` 表
- [ ] 记录 llm_model, llm_provider, token_usage
- [ ] 使用 JSON Mode 强制输出格式
- [ ] 状态更新为 `evaluated`
- [ ] Typecheck 通过

## Dependencies

Issue #5

## Type

backend

## Priority

P0
