# RIP-006 Tests

## Automated

- Structured response parsing succeeds and malformed JSON retries once.
- Unknown operations and forbidden fields are rejected.
- Proposal creation does not mutate a draft.
- Selected apply increments revision once; stale apply returns a conflict.
- Reject leaves draft content unchanged.
- Undo restores the stored snapshot only at the expected revision.
- Frontend lint and production build pass.

Evidence recorded on 2026-08-03:

- Backend unit suite: 145 passed, 1 skipped.
- RIP-006 PostgreSQL integration suite: 3 passed.
- Ruff and targeted strict mypy: passed.
- Frontend lint and production build: passed.
- Alembic current/head: `h8c9d0e1f2a3`.

## Browser

- Desktop: the content list scrolls independently and the assistant opens in the
  middle panel without adding another permanent column.
- Tablet: the assistant does not reduce the preview to an unusable width.
- Mobile: the assistant panel and sticky composer remain usable without overlap.
- Empty, loading, proposal, applied, rejected, conflict, and failure states render.

Browser verification is pending. The Chrome extension connection timed out, the
in-app browser was unavailable, and the local Chromium process was denied by the
macOS sandbox before page creation.
