# [RIP-010] Vision transcription and JD processing pipeline

## Description

Add guarded Vision transcription and text-quality stages, then feed the validated transcription into the existing duplicate check and text JDExtractor rather than creating a second structured JD path.

## Acceptance Criteria

- [ ] Add `source_validate`, `vision_extract` and `text_quality_check` transitions with current-run ownership checks
- [ ] Build ordered multimodal input from persisted assets through the active verified Vision configuration
- [ ] Validate page/asset IDs, order, bounded text and warning fields with Pydantic
- [ ] Concatenate page text into `raw_text`, retain page mapping and record provider/model/transcriber version without persisting request payloads
- [ ] Enforce 30~100000 visible-character quality bounds and fail empty/incomplete transcription without creating ready data
- [ ] Reuse existing normalization, duplicate detection, field-source merge and `JDExtractor.extract(raw_text)`
- [ ] Apply bounded transport retry and one schema-correction attempt; retry/reextract creates a new run id
- [ ] Stale/deleted runs are no-ops and cannot update asset/JD state
- [ ] Worker tests cover success, no text, malformed IDs/JSON, timeout, 429, retry exhaustion and stale workers
- [ ] Regression tests cover text/file/url imports and manual-field protection

## Dependencies

- `tasks/issues/issue-094-rip010-jd-image-import-api.md`

## Type

backend / workflow

## Priority

high

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - US-002, US-003; FR-3~FR-10

## SPEC Reference

`specs/RIP-010-jd-vision-import/spec.md` - Sections 6.1, 6.3, 7, 11
