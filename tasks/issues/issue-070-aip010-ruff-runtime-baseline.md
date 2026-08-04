# [AIP-010] Restore Ruff and runtime metadata baseline

Resolve the reviewed Ruff/runtime compatibility findings and align declared Python support with the actual Python 3.12 target.

## Acceptance Criteria
- [ ] `ruff check backend` and `ruff format --check backend` pass without new ignores
- [ ] Undefined names, unused/import-order, and line-width findings are fixed at their source
- [ ] `requires-python`, Ruff, mypy, local docs, and CI target one compatible runtime contract
- [ ] Targeted behavior tests pass after cleanup

- **Type:** backend
- **Priority:** high
- **Depends on:** #069
- **SPEC:** `specs/AIP-010-ci-test-quality-gates/spec.md` (Sections 5, 11)
