# [RIP-008] Structured LLM plan generator

## Description

Generate actionable, evidence-backed task drafts across all required categories with deterministic server-side schedule normalization.

## Acceptance Criteria
- [ ] Add plan-generation prompt and `LLMPlanGenerator` using Source Catalog boundaries
- [ ] Worker-facing generator uses active verified DB config and `LLMGateway.from_config`
- [ ] Output contains 6~30 tasks and at least one task in each of six categories
- [ ] Every AI task contains only known basis IDs and never claims unsupported candidate experience
- [ ] Unknown basis, missing category, duplicate title, invalid length or malformed JSON triggers schema failure
- [ ] Server converts due offsets to Asia/Shanghai dates, defaulting to 28-day horizon/8 weekly hours and clamping target date
- [ ] Input snapshot is sanitized and records model/match reference
- [ ] Unit tests cover valid output, every schema failure, prompt injection content and schedule edges

## Dependencies

- `tasks/issues/issue-049-rip008-plan-source-catalog.md`

## Type

backend / AI

## Priority

high

## PRD Reference

`tasks/prd-job-search-plans.md` - US-003; FR-7~FR-10

## SPEC Reference

`specs/RIP-008-job-search-plans/spec.md` - RIP-008 Sections 3.4, 5.3, 7.2

