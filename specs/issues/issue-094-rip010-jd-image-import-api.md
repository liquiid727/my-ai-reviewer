# [RIP-010] JD image assets, validation and import API

## Description

Persist ordered JD image assets and expose an asynchronous multi-image import endpoint with bounded decode validation, storage compensation and run ownership.

## Acceptance Criteria

- [ ] Add `jd_source_assets` and extend JD source/processing constraints through an Alembic migration
- [ ] Add `POST /api/v1/jd/import/images` using repeated multipart files and the standard API envelope
- [ ] Accept only PNG, JPG/JPEG and WEBP; enforce 1~8 files, 10MB each, 30MB total, 25MP and 4000px maximum normalized edge
- [ ] Validate extension, declared MIME, magic bytes and actual decode format; reject empty, corrupted, spoofed and decompression-bomb inputs before dispatch
- [ ] Strip EXIF, retain stable order and upload only sanitized image objects
- [ ] Require explicit acknowledgement that images are sent to the configured external Vision provider
- [ ] Persist JD/assets/run atomically where possible and compensate MinIO objects on partial failure
- [ ] Return processing state immediately and map validation, storage, config and broker failures to safe errors
- [ ] API/migration tests cover success, every limit, object cleanup and legacy `/jd/import/file` regression

## Dependencies

- `tasks/issues/issue-092-jd-intelligence-drift-baseline.md`
- `tasks/issues/issue-093-rip010-llm-multimodal-capabilities.md`

## Type

backend / database / API

## Priority

high

## PRD Reference

`spec-draft/jd-intelligence-v2-2026-08-05.md` - US-001, US-004; FR-1~FR-5, FR-7, FR-29

## SPEC Reference

`specs/RIP-010-jd-vision-import/spec.md` - Sections 6.1~6.2, 7.1, 9~10
