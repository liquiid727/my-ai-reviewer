# Dedicated Section Split Step + Missing Section Types

## Description

PRD §3.1/§4 要求 Section 作为独立的自动识别步骤，覆盖 8 类：Basic Information / Education / Work Experience / Projects / Skills / Certificates / Awards / Self Evaluation。当前分区依赖 LLM 抽取顺带产出，且缺 basic_info / awards / self_evaluation。将 Section 切分做成可追溯的独立环节。

PRD Reference: docs/prd/parser.md §3.1, §4

## Acceptance Criteria

- [ ] `backend/domain/resume/enums.py`：`ResumeSectionType` 增加 `AWARDS`、`SELF_EVALUATION`
- [ ] 新增基于标题启发式的 section 切分器（`backend/infrastructure/extractors/` 下），产出 section_type + title + raw_text
- [ ] `_persist_sections` 覆盖 basic_info/awards/self_evaluation
- [ ] section 切分独立于 LLM profile 输出，可单独测试
- [ ] 单测覆盖标题识别与 8 类映射
- [ ] Typecheck 通过

## Dependencies

Issue #28

## Type

backend

## Priority

medium
