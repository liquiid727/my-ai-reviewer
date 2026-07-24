# Extraction Field Gaps (GPA / tech_stack / industry / 难点 / 团队规模)

## Description

对齐 PRD §5「AI 信息抽取」的字段要求，补齐当前 CandidateProfile schema 与抽取 prompt 缺失的字段，并修正字段拼写。当前实现缺：教育 GPA、工作经历 tech_stack/industry、项目 难点(difficulties)/团队规模(team_size)；`ProjectExperience.responsibilitity` 拼写错误。

PRD Reference: docs/prd/parser.md §5

## Acceptance Criteria

- [ ] `backend/domain/resume/schemas.py`：`Education` 增加 `gpa: Optional[str]`
- [ ] `WorkExperience` 增加 `tech_stack: List[str] = []` 和 `industry: Optional[str] = None`
- [ ] `ProjectExperience` 增加 `difficulties: List[str] = []`、`team_size: Optional[str] = None`
- [ ] 修正 `ProjectExperience.responsibilitity` → `responsibility`（兼容旧数据反序列化）
- [ ] `backend/infrastructure/llm/prompts/extraction.py`：prompt 明确要求输出上述新字段
- [ ] `backend/domain/resume/services.py::_persist_sections` / `_upsert_candidate_profile` 正确落库新字段
- [ ] 现有单测更新，新增字段有覆盖
- [ ] Typecheck 通过

## Dependencies

None

## Type

backend

## Priority

high
