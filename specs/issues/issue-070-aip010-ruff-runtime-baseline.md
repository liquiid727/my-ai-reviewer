# [AIP-010] Restore Ruff and runtime metadata baseline

Resolve the reviewed Ruff/runtime compatibility findings and align declared Python support with the actual Python 3.12 target.

## Acceptance Criteria
- [x] `ruff check backend` and `ruff format --check backend` pass without new ignores
- [x] Undefined names, unused/import-order, and line-width findings are fixed at their source
- [x] `requires-python`, Ruff, mypy, local docs, and CI target one compatible runtime contract
- [x] Targeted behavior tests pass after cleanup

- **Type:** backend
- **Priority:** high
- **Depends on:** #069
- **SPEC:** `specs/AIP-010-ci-test-quality-gates/spec.md` (Sections 5, 11)

## Evidence (2026-08-04)

| Command | Result |
|---|---|
| `PYTHONPATH=. uv run --project backend ruff check backend` | PASS (0 findings) |
| `PYTHONPATH=. uv run --project backend ruff format --check backend` | PASS (206 files) |
| `PYTHONPATH=. uv run --project backend pytest backend/tests/unit -q --tb=no` | PASS (210 passed) |
| `git diff --check` | PASS |

Runtime contract locked to Python 3.12:
- `backend/pyproject.toml`: `requires-python = ">=3.12"`, Ruff `target-version = "py312"`, mypy `python_version = "3.12"`
- Docs/scripts aligned: `AGENTS.md`, `backend/README.md`, `README.md`, `scripts/setup.sh`
- Evidence: `tests/results/20260804-aip010-issue-070-ruff-runtime.json`
