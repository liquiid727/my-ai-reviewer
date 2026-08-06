# [RIP-010] Vision import security and acceptance closeout

## Description

Close RIP-010 with migration, provider-adapter, workflow, storage, privacy-log and browser evidence using synthetic JD images.

## Acceptance Criteria

- [ ] Run migration upgrade and downgrade guard tests against the actual Alembic head
- [ ] Verify OpenAI and Anthropic adapter fixtures without live provider calls; optionally record a separate configured-provider smoke test
- [ ] Execute image upload -> Vision transcription -> duplicate check -> JDExtractor -> ready flow with synthetic fixtures
- [ ] Verify failed, retried, deleted and stale-worker branches and MinIO cleanup
- [ ] Assert logs, errors, task metadata and snapshots contain no base64, full transcription, prompt or API key canaries
- [ ] Run legacy text/file/url imports, synchronous JD create, edit/reextract and `rules_v1` regression tests
- [ ] Perform desktop/mobile browser acceptance for upload, progress, ready, failure and retry
- [ ] Update database/backend/frontend design and RIP-010 tasks to reflect as-built behavior only
- [ ] Record exact lint/type/test/build/browser statuses; NOT_RUN/BLOCKED are not PASS
- [ ] `git diff --check` and final scoped `git status --short` inspection pass

## Dependencies

- `tasks/issues/issue-096-rip010-jd-image-import-ui.md`

## Type

fullstack / qa / security

## Priority

high

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - US-001~US-004, US-010; Success Metrics

## SPEC Reference

`specs/RIP-010-jd-vision-import/spec.md` - Sections 11~12
