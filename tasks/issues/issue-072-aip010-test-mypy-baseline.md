# [AIP-010] Restore test-double and optional-dependency typing baseline

Make backend test fakes/spies and optional imaging paths satisfy the same strict typing contract as production code.

## Acceptance Criteria
- [ ] Full `mypy backend` passes, including tests
- [ ] Test doubles implement the exact Protocol/call signatures they replace
- [ ] Installed and unavailable optional-dependency paths remain covered
- [ ] No directory-wide test ignore or weakened strict mode is introduced

- **Type:** test
- **Priority:** high
- **Depends on:** #071
- **SPEC:** `specs/AIP-010-ci-test-quality-gates/spec.md` (Sections 5, 11)
