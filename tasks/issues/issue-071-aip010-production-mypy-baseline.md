# [AIP-010] Restore production-code mypy baseline

Eliminate strict mypy errors in production backend modules without broad ignores or weakening public types.

## Acceptance Criteria
- [ ] Strict mypy passes for production packages
- [ ] Pydantic, SQLAlchemy, API parameter, async return, and optional-value contracts are explicit
- [ ] Provider/optional dependency overrides are module-specific and justified
- [ ] No `Any`, cast, or ignore is added only to silence a real contract mismatch

- **Type:** backend
- **Priority:** high
- **Depends on:** #070
- **SPEC:** `specs/AIP-010-ci-test-quality-gates/spec.md` (Sections 5, 7)
