# [RIP-012] Add image JD import through the OCR registry

Add bounded PNG/JPEG JD import that reuses the shipped RIP-001 OCR parser and enters the versioned review workflow.

## Acceptance Criteria

- [ ] Validate extension, MIME, magic bytes, size, dimensions, and decode bounds before storage.
- [ ] Persist JD identity/source object before dispatch and return a run-owned processing state.
- [ ] Resolve OCR through the existing parser registry without importing a provider SDK into JD code.
- [ ] Feed normalized OCR text into duplicate detection and RIP-011 extraction/review.
- [ ] Handle no-text, parser unavailable, timeout, missing object, retry, cleanup, and stale-run paths safely.
- [ ] Synthetic PNG/JPEG unit/integration/storage tests pass.

- **Type:** backend
- **Priority:** high
- **Depends on:** issue #030, #102
- **SPEC:** RIP-012 sections 6.1, 7.1/7.2, 9, 11
