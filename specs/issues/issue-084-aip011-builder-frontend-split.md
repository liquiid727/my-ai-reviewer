# [AIP-011] Split Builder frontend and unify transport state

Reduce `BuilderPage` to route composition and move cohesive editor/export/assistant/photo workflows into feature components and hooks.

## Acceptance Criteria
- [ ] `BuilderPage` no longer owns unrelated editor, assistant, export, photo, polling, and error responsibilities
- [ ] Standard JSON calls use the shared client; multipart/binary exceptions stay isolated in Builder API
- [ ] Polling/cancellation and code/HTTP error decoding have one owner
- [ ] Component/browser tests cover loading, empty, success, failure, pending, conflict, export, and responsive paths

- **Type:** frontend
- **Priority:** medium
- **Depends on:** #075, #081
- **SPEC:** `specs/AIP-011-architecture-modularization/spec.md` (Sections 5, 8-11)
