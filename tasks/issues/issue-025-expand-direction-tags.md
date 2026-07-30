# Expand Classification Direction Tags

## Description

PRD §6 要求的方向标签远多于现有实现。当前 `rule_classifier` 仅支持 Backend/Frontend/AI/DevOps/Data，缺少 LLM Engineer、Architect、Game、Finance、E-commerce、Cloud Native、Distributed System 等。扩展关键词映射并允许基于工作/项目文本（非仅 skills）命中。

PRD Reference: tasks/prd-parser.md §6

## Acceptance Criteria

- [ ] `backend/infrastructure/classifiers/rule_classifier.py`：`TECH_DIRECTION_KEYWORDS` 扩展新增方向（LLM Engineer / Architect / Cloud Native / Distributed System / Game 等）
- [ ] 方向匹配来源扩展到 skills + projects.tech_stack + work responsibilities
- [ ] 行业类标签（Finance/E-commerce 等）与技术方向标签区分清晰
- [ ] classifier version 升级（如 rule-classifier-v2）
- [ ] 单测覆盖新增方向命中
- [ ] Typecheck 通过

## Dependencies

Issue #23

## Type

backend

## Priority

medium
