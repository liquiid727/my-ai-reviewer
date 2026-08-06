# [RIP-011] Evidence Catalog and LLM multidimensional matcher

## Description

Build a minimized Source Catalog from structured JD and approved masked Resume Facts/Profile, then use a structured LLM matcher whose every conclusion must cite valid catalog evidence.

## Acceptance Criteria

- [ ] Build deterministic JD and candidate evidence IDs from a single immutable input snapshot
- [ ] Exclude identity, raw resume text and unrelated fields from Catalog, snapshot and prompt
- [ ] Run `PrivacyGuard` fail closed before LLM dispatch and validate safe structured output after response
- [ ] Prompt and Pydantic output cover all seven dimensions with nullable score, status, reason, evidence IDs and confidence
- [ ] Reject unknown, duplicate, wrong-source or cross-input evidence references and out-of-range values
- [ ] Treat unsupported dimensions as unknown instead of inventing evidence
- [ ] Retry malformed JSON/schema/evidence once, then fail without returning partial ready scores
- [ ] Record prompt/schema/provider/model identity and token/latency metadata without prompt content
- [ ] Unit tests cover normal, sparse evidence, conflict, hallucinated IDs, malformed JSON, retry exhaustion and provider errors
- [ ] LLM spy tests prove no raw resume, identity or direct identifier reaches the provider

## Dependencies

- `tasks/issues/issue-093-rip010-llm-multimodal-capabilities.md`
- `tasks/issues/issue-098-rip011-matching-contracts.md`
- `tasks/issues/issue-099-rip011-hard-filter-policy.md`

## Type

backend / application / infrastructure

## Priority

high

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - US-006; FR-14~FR-17, FR-20, FR-28

## SPEC Reference

`specs/RIP-011-evidence-bound-jd-matching/spec.md` - Sections 6.1, 6.3~6.4, 7.1~7.2
