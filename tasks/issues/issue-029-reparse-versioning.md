# Re-parse / Parser Version Retrace Mechanism

## Description

PRD §3.1/§4 要求 Parser 支持版本化以便「重新解析」。当前仅记录 `parser_version`，无重解析入口，也不保留历史。提供按新 parser/extractor 版本对已存简历重跑流水线的能力，并保留可追溯记录。

PRD Reference: docs/prd/parser.md §3.1, §4

## Acceptance Criteria

- [ ] 新增重解析入口（service + API 或 task），可对指定 resume_id 触发从 text_extract 起的重跑
- [ ] 重解析幂等：facts/sections/profile 覆盖前保留上一版本快照（版本号或时间戳标记）
- [ ] `ResumeModel` 记录 parser_version / extractor_version 变更
- [ ] 重解析不破坏已有 evaluation/interview 关联
- [ ] 单测覆盖重解析触发与版本记录
- [ ] Typecheck 通过

## Dependencies

Issue #28

## Type

backend

## Priority

low
