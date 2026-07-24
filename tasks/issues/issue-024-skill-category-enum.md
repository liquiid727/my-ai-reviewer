# Skill Category Enum Constraint (10 fixed categories)

## Description

PRD §5「技能」要求固定 10 类技能分类：Programming Language / Framework / Database / Cache / MQ / Cloud Native / AI / DevOps / Testing / Architecture。当前 `Skill.category` 为自由字符串，无约束，导致分类器与下游统计不稳定。引入枚举并在抽取 prompt 中约束模型输出。

PRD Reference: docs/prd/parser.md §5

## Acceptance Criteria

- [ ] `backend/domain/resume/enums.py`：新增 `SkillCategory` 枚举（10 类 + `other` 兜底）
- [ ] `backend/domain/resume/schemas.py`：`Skill.category` 使用枚举校验（非法值归一到 `other`）
- [ ] `backend/infrastructure/llm/prompts/extraction.py`：prompt 列出 10 类允许值
- [ ] `RuleBasedResumeClassifier` 的技术深度统计基于枚举类别
- [ ] 单测覆盖枚举校验与兜底
- [ ] Typecheck 通过

## Dependencies

Issue #23

## Type

backend

## Priority

medium
