# [AIP-010] Add frontend test harness and critical state tests

Add a React component/workflow test command and protect the highest-risk UI state contracts.

## Acceptance Criteria
- [ ] `pnpm test`/`make test-frontend` runs deterministically in CI mode
- [ ] Upload/privacy review and Builder save/conflict/error states have synthetic component tests
- [ ] Polling cleanup/terminal/timeout ownership is tested
- [ ] Frontend test, Oxlint, TypeScript, and production build pass

- **Type:** frontend
- **Priority:** high
- **Depends on:** #069
- **SPEC:** `specs/AIP-010-ci-test-quality-gates/spec.md` (Sections 5, 11)
