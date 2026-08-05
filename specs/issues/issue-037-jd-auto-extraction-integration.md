# POST /jd 自动抽取集成 + Alembic 迁移

## Description

将 `JDExtractor` 接入 `POST /jd`：未传 `required_skills` 且 `raw_text` 非空时自动 LLM 抽取（`extraction_source="llm"`）；显式传入时跳过抽取（`extraction_source="manual"`）。抽取失败返回 502 且不落库，避免产生空技能 JD 污染匹配。同步 Alembic 迁移为 `job_descriptions` 补字段。

PRD Reference: tasks/prd-resume-toolchain-increments.md US-006 / FR-12
SPEC Reference: specs/RIP-003-jd-matching/spec.md「增量设计（v1.1）：LLM JD 抽取器」

## Acceptance Criteria

- [x] `POST /jd` 未传 `required_skills` 且 `raw_text` 非空 → 调用 JDExtractor，结果落库，`extraction_source="llm"`
- [x] 显式传入 `required_skills` → 跳过抽取，`extraction_source="manual"`（现有调用方行为不变，回归单测保证）
- [x] 抽取失败 → HTTP 502 `JD_EXTRACTION_FAILED`，JD 不落库
- [x] Alembic 迁移：`job_descriptions` 新增 `responsibilities` / `seniority` / `extraction_source` 字段（接续现有迁移链）
- [x] 单测：自动抽取 / 手动跳过 / 502 不落库三路径（mock extractor）
- [x] Lint / mypy 通过；`alembic upgrade head` 本地验证

> Shipped: PR #16（squash 入 main a516a4a）

## Dependencies

Issue #36

## Type

backend

## Priority

high
