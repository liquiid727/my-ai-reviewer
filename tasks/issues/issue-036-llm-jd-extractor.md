# LLM JD 抽取器（required_skills + evidence）

## Description

当前 `POST /jd` 要求调用方手动传 `required_skills`，与 RIP-003 spec 的 LLM 抽取设计不符。新增 `JDExtractor`：复用 `LLMGateway`（与 `llm_extractor.py` 同模式），从 JD 原文抽取 required_skills / critical_skills / responsibilities / seniority，每项技能附原文 evidence 便于追溯。

PRD Reference: tasks/prd-resume-toolchain-increments.md US-005 / FR-11
SPEC Reference: specs/RIP-003-jd-matching/spec.md「增量设计（v1.1）：LLM JD 抽取器」

## Acceptance Criteria

- [x] 新增 `backend/infrastructure/extractors/jd_extractor.py`：`JDExtractor.extract(raw_text) -> JDExtraction`
- [x] 输出结构含 required_skills / critical_skills / responsibilities / seniority（junior/mid/senior/expert 四档），技能项带原文 evidence
- [x] LLM 输出不合法（JSON 解析或 schema 校验失败）→ 内部重试 1 次；仍失败 → 抛 `JDExtractionError`
- [x] Prompt 与解析逻辑与 `llm_extractor.py` 风格一致（结构化输出 + pydantic 校验）
- [x] 单测：正常抽取 / 输出畸形重试成功 / 重试仍失败三路径（mock LLMGateway，共 6 条含空 JSON 与截断）
- [x] Lint / mypy 通过

> Shipped: PR #15（squash 入 main 313c534）

## Dependencies

None

## Type

backend

## Priority

high
