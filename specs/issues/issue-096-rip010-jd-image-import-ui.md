# [RIP-010] JD image import and recovery UI

## Description

Extend the existing JD Library import dialog and detail page with multi-image selection, external-provider disclosure, upload validation, processing progress and recovery states.

## Acceptance Criteria

- [ ] Add an image import mode to the existing JD import dialog; do not create an isolated route
- [ ] Preserve selected image order and show allowed types/count/size before submission
- [ ] Require a visible acknowledgement that images are sent to the configured Vision provider
- [ ] Settings UI displays current Vision/structured-output capability and latest verification time from the typed configuration API
- [ ] Cover empty, invalid, uploading, processing, ready, failed, retry pending and expired-source states
- [ ] Poll with one timer and stop on terminal state, timeout, page hide, unmount or JD change
- [ ] Ready state navigates to or refreshes the editable JD detail
- [ ] Error messages use safe mapped copy and never display provider bodies, object keys or image content
- [ ] Update typed API boundaries and Chinese/English i18n resources
- [ ] Component tests and desktop/mobile browser verification cover success, validation failure, processing failure and retry

## Dependencies

- `tasks/issues/issue-095-rip010-vision-processing-pipeline.md`

## Type

frontend / ui

## Priority

high

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - US-001~US-004; FR-25, FR-29

## SPEC Reference

`specs/RIP-010-jd-vision-import/spec.md` - Sections 5, 7.3, 9, 11~12
