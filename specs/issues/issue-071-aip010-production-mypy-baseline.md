# [AIP-010] Restore production-code mypy baseline

Eliminate strict mypy errors in production backend modules without broad ignores or weakening public types.

## Acceptance Criteria
- [x] Strict mypy passes for production packages
- [x] Pydantic, SQLAlchemy, API parameter, async return, and optional-value contracts are explicit
- [x] Provider/optional dependency overrides are module-specific and justified
- [x] No `Any`, cast, or ignore is added only to silence a real contract mismatch

- **Type:** backend
- **Priority:** high
- **Depends on:** #070
- **SPEC:** `specs/AIP-010-ci-test-quality-gates/spec.md` (Sections 5, 7)

**Status:** accepted (local-reviewed)

## Evidence
- Date: 2026-08-04
- Report: `tests/results/20260804T070313Z-aip010-issue-071-production-mypy.json`
- Production mypy: `Success: no issues found in 161 source files` (exit 0)
- Full `mypy backend`: 203 errors, all under `backend/tests/` (prod 0) — deferred to #072
- Targeted unit: 20 passed (`test_pagination`, `test_privacy_builder_export`, `test_resume_builder_services`, `test_photo_rendering`)

## Notes
- Invoke mypy from repo root with `--config-file backend/pyproject.toml` (no root pyproject); otherwise celery/imaging overrides are not loaded.
- Source fixes: `pdf_renderer` uses `pymupdf` (aligned with `pdf_parser`) + `int(page_count)`; `export_draft_pdf` builds `set[str]` tokens with explicit `isinstance` guards.
- No new `[[tool.mypy.overrides]]` entries. Existing justified overrides remain: celery (no py.typed), cv2/rembg/numpy (optional imaging extras).
- Line-local `# type: ignore[no-untyped-call]` on pymupdf open/close only — same pattern as `pdf_parser.py`; not used to hide contract mismatches.
