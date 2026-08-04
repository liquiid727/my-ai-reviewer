# [AIP-010] Add GitHub quality workflow and activation runbook

Create stable hosted CI jobs equivalent to local gates and document the separately authorized branch-protection step.

## Acceptance Criteria
- [ ] Workflow exposes the six stable check names from `rules/quality-gates.md`
- [ ] Python 3.12, lockfile installs, PostgreSQL/Redis services, caches, and synthetic configuration are explicit
- [ ] Test/coverage artifacts are safe and each job preserves its failure result
- [ ] Runbook separates workflow merge from external required-check activation and rollback

- **Type:** infra
- **Priority:** high
- **Depends on:** #074, #075
- **SPEC:** `specs/AIP-010-ci-test-quality-gates/spec.md` (Sections 5, 11-12)
