# Evaluation: Communication Dimension + Per-Dimension Evidence

## Description

PRD §7 要求 9 个评估维度（当前强制 8 个，缺「沟通表达（从简历推断）」），且每维需给出 Score/Reason/Evidence（当前 `DimensionScore` 只有 score+comment，Evidence 未强制）。补齐维度并在维度级增加 evidence 字段。

PRD Reference: tasks/prd-parser.md §7

## Acceptance Criteria

- [ ] `backend/infrastructure/evaluators/llm_evaluator.py`：`REQUIRED_DIMENSIONS` 增加「沟通表达」
- [ ] `backend/domain/resume/schemas.py`：`DimensionScore` 增加 `evidence: Optional[str]`（reason 对应 comment）
- [ ] `backend/infrastructure/llm/prompts/evaluation.py`：prompt 要求 9 维度且每维输出 evidence
- [ ] `_validate` 校验 9 个必需维度齐全
- [ ] 单测更新维度集合与 evidence 存在性
- [ ] Typecheck 通过

## Dependencies

None

## Type

backend

## Priority

high
