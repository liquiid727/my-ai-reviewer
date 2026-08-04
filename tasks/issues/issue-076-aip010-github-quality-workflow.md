# [AIP-010] Add GitHub quality workflow and activation runbook

Create stable hosted CI jobs equivalent to local gates and document the separately authorized branch-protection step.

## Acceptance Criteria
- [x] Workflow exposes the six stable check names from `rules/quality-gates.md`
- [x] Python 3.12, lockfile installs, PostgreSQL/Redis services, caches, and synthetic configuration are explicit
- [x] Test/coverage artifacts are safe and each job preserves its failure result
- [x] Runbook separates workflow merge from external required-check activation and rollback

- **Type:** infra
- **Priority:** high
- **Depends on:** #074, #075
- **SPEC:** `specs/AIP-010-ci-test-quality-gates/spec.md` (Sections 5, 11-12)
- **Status:** implemented (local-reviewed pending)
- **Evidence:** `tests/results/20260804T083600Z-aip010-issue-076-github-quality-workflow-r2.json`
- **Runbook:** `docs/ci/branch-protection-activation.md`
- **Workflows:** `.github/workflows/{quality,test,build}.yml`
