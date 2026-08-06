# [RIP-012] Interview JD and match context integration

## Description

Add optional structured JD and fresh match references to Interview creation while preserving legacy `jd_text` and current resume/draft privacy behavior.

## Acceptance Criteria

- [ ] Add optional `jd_id` and `match_result_id` fields without changing the existing resume/draft exclusive-input rule
- [ ] Require `jd_text` or `jd_id`; require `jd_id` when `match_result_id` is supplied
- [ ] Validate the match belongs to the same resume/JD, is ready and is fingerprint-fresh
- [ ] Preserve old `jd_text`-only clients and existing response envelope
- [ ] Persist a minimal immutable structured JD/match context snapshot and fingerprint at interview creation
- [ ] Feed only approved masked candidate context and bounded match evidence into question/report prompts
- [ ] Fail closed on privacy violations and return safe errors for missing, cross-resource, failed or stale matches
- [ ] Tests cover resume and draft paths, old jd_text, jd_id only, fresh match, stale/cross-resource rejection and snapshot immutability
- [ ] Existing interview task run/retry behavior remains compatible

## Dependencies

- `tasks/issues/issue-101-rip011-async-matching-api.md`
- RIP-009 privacy baseline

## Type

backend / API / integration

## Priority

medium

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - US-009; FR-27~FR-29

## SPEC Reference

`specs/RIP-012-jd-matching-consumption/spec.md` - Sections 7.3, 9.3, 10~11
