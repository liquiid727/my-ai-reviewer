# [AIP-010] Add shared quality scripts and Make targets

Implement deterministic read-only gate scripts and the stable Make interfaces defined by the quality rules.

## Acceptance Criteria
- [x] `make lint`, `type-check`, `arch-check`, `test-unit`, `test-integration`, `test-frontend`, `build`, `ci-fast`, and `ci` exist
- [x] Targets preserve underlying exit codes, identify the failing gate, and never auto-fix source
- [x] Local and future hosted CI call shared scripts/commands
- [x] Missing integration prerequisites produce a non-zero, explicit blocker rather than a false pass

- **Type:** infra
- **Priority:** high
- **Depends on:** #071, #072, #073
- **SPEC:** `specs/AIP-010-ci-test-quality-gates/spec.md` (Sections 7-8)
