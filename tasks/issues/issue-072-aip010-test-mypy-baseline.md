# [AIP-010] Restore test-double and optional-dependency typing baseline

Make backend test fakes/spies and optional imaging paths satisfy the same strict typing contract as production code.

## Acceptance Criteria
- [x] Full `mypy backend` passes, including tests
- [x] Test doubles implement the exact Protocol/call signatures they replace
- [x] Installed and unavailable optional-dependency paths remain covered
- [x] No directory-wide test ignore or weakened strict mode is introduced

- **Type:** test
- **Priority:** high
- **Depends on:** #071
- **SPEC:** `specs/AIP-010-ci-test-quality-gates/spec.md` (Sections 5, 11)

## Evidence
- Status: PASS (local-reviewed)
- Full mypy: `PYTHONPATH=. uv run --project backend mypy backend --config-file backend/pyproject.toml` → Success: no issues found in 206 source files
- Ruff: backend/tests + minimal production re-exports clean
- Unit subset: 158 passed (touched test modules)
- Evidence JSON: `tests/results/20260804T071811Z-aip010-issue-072-test-mypy.json`
