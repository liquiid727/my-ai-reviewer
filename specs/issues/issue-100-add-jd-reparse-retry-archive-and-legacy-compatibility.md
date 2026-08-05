# [RIP-011] Add JD reparse, retry, archive, and legacy compatibility

Complete the versioned lifecycle around failed/reparsed drafts while preserving current versions and existing callers.

## Acceptance Criteria

- [ ] Reparse creates a new run/draft, protects manual fields by default, and never mutates current/history versions.
- [ ] Retry resumes from the latest safe step with a new run ID; broker/timeout failures are durable and safe.
- [ ] Add abandon-draft and archive commands; referenced identities cannot hard-delete.
- [ ] Reparse failure leaves current version usable and visible.
- [ ] Preserve legacy JD endpoints/fields while marking new downstream paths version-pinned.
- [ ] Integration tests cover duplicate, retry, stale worker, archive, referenced delete, and legacy consumers.

- **Type:** backend
- **Priority:** high
- **Depends on:** #099
- **SPEC:** RIP-011 sections 6.2/6.3, 7.2/7.3, 9.3
