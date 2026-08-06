# [RIP-010] LLM capability registry and multimodal adapters

## Description

Add an explicit, provider-neutral capability and multimodal message contract. Implement tested OpenAI and Anthropic image-block conversion without inferring Vision support from model names.

## Acceptance Criteria

- [ ] Add `capabilities` and `capabilities_verified_at` to LLM configuration with Alembic migration and backward-compatible text defaults
- [ ] Define typed text/image content blocks and `complete_multimodal()` outside provider-specific modules
- [ ] Convert canonical image blocks correctly in OpenAI and Anthropic adapters
- [ ] Reject image calls when `supports_vision` is false/unknown, the configuration is unverified or configured limits are exceeded
- [ ] Custom/DeepSeek OpenAI-compatible endpoints require explicit Vision capability
- [ ] LLM configuration API exposes Vision and structured-output capability plus verification time through typed schemas
- [ ] Apply separate multimodal timeout and bounded retry classification
- [ ] Unit tests assert payload conversion and that logs/errors never contain base64, prompt content or API keys
- [ ] Existing text `complete()` callers and LLM configuration tests remain compatible

## Dependencies

- `tasks/issues/issue-092-jd-intelligence-drift-baseline.md`

## Type

backend / infrastructure

## Priority

high

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - US-002, US-004; FR-4, FR-5, FR-9, FR-28

## SPEC Reference

`specs/RIP-010-jd-vision-import/spec.md` - Sections 6.4, 7.2~7.3, 8, 10~12
