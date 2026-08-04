# Quality Gate Rules

**Rule set:** QG-1
**Applies to:** implementation, review, merge, and release decisions
**Design source:** `design/quality-architecture.md`

## Gate Status Vocabulary

- `PASS`: the exact recorded command completed successfully and its assertions/thresholds passed.
- `FAIL`: the command ran and found a static, behavioral, contract, or threshold failure.
- `BLOCKED`: the command could not exercise its required scope because an external service, dependency, permission, or environment was unavailable.
- `NOT_RUN`: no execution was attempted. It is never equivalent to `PASS` or `BLOCKED`.

## Required Gates

| Gate ID | Scope | Current direct command | Target entry point |
|---|---|---|---|
| `lint-backend` | Ruff rules | `PYTHONPATH=. uv run --project backend ruff check backend` | `make lint` |
| `format-backend` | Ruff formatting | `PYTHONPATH=. uv run --project backend ruff format --check backend` | `make lint` |
| `type-backend` | strict mypy | `PYTHONPATH=. uv run --project backend mypy backend` | `make type-check` |
| `lint-frontend` | Oxlint | `cd frontend && pnpm lint` | `make lint` |
| `build-frontend` | TypeScript + Vite build | `cd frontend && pnpm build` | `make build` / `make ci` |
| `test-backend-unit` | backend unit tests | `PYTHONPATH=. uv run --project backend pytest backend/tests/unit -q` | `make test-unit` |
| `test-backend-integration` | DB/API integration | `PYTHONPATH=. uv run --project backend pytest backend/tests/integration -q` | `make test-integration` |
| `test-frontend` | component/workflow tests | unavailable until AIP-010 | `make test-frontend` |
| `architecture` | dependency and exception rules | manual/import scan until AIP-011 | `make arch-check` |
| `diff-integrity` | whitespace/conflict markers and final scope | `git diff --check` plus `git status --short` | `make ci` retains explicit evidence |

QA MUST inspect the Makefile/package scripts before using a target. A target listed as planned above MUST be reported as `NOT RUN` if it does not exist; QA then runs the current direct command where possible.

## Target Make Contract

AIP-010 implements these stable interfaces:

- `make lint`: backend Ruff check + format check + frontend lint; no mutation and no `--fix`.
- `make type-check`: strict backend mypy plus explicit frontend TypeScript checking.
- `make arch-check`: executable dependency rules and expiring exception registry.
- `make test-unit`: deterministic backend and frontend unit tests without external services.
- `make test-integration`: service-backed integration/API tests; missing services fail as `BLOCKED`, not silent skip.
- `make test`: the documented complete test set, preserving backward compatibility with current backend coverage.
- `make build`: frontend production build and other required build validation.
- `make ci-fast`: lint, type, architecture, unit, and frontend build.
- `make ci`: full required local gate, including integration tests when prerequisites are available.

Make targets and GitHub Actions MUST call shared scripts/commands so local and hosted semantics do not diverge.

## Blocking Policy

- Any unresolved P0/P1 finding, lint/type/architecture error, failed required test, failed build, invalid migration, or privacy leak blocks merge.
- Required integration behavior failures block merge. An unavailable external service is `BLOCKED` and requires a recorded decision; it is not a test skip or pass.
- New warnings, skips, `xfail`, ignores, coverage exclusions, architecture exceptions, or lint/type suppressions require explicit justification and ownership.
- A change MUST NOT make the measured baseline worse, even during ratchet adoption.
- No command may use `--fix`, delete snapshots, rewrite assertions, hide stderr, or relax configuration as part of a verification target.

## Coverage Policy

Repository coverage is measure-only until AIP-010 records a reproducible baseline. The first enforced threshold is the accepted baseline rounded down to a whole percentage; later increases are tracked by issue. Critical privacy, error mapping, state transition, retry/ownership, and LLM guard modules require branch-focused acceptance tests regardless of the aggregate percentage.

Coverage decreases, new untested public behavior, and excluded critical paths fail the gate. A single arbitrary percentage MUST NOT replace requirement-to-test mapping.

## Hosted CI Contract

Target required check names are stable:

- `quality / lint-and-type`
- `quality / architecture`
- `test / backend-unit`
- `test / backend-integration`
- `test / frontend`
- `build / frontend`

CI pins Python 3.12 and the repository's package-manager versions, restores lockfile-based dependencies, uses synthetic data, and uploads normalized reports without secrets/PII. Branch protection activation requires explicit ship/repository authorization and is recorded separately from workflow creation.

## Evidence Format

Every normalized result under `tests/results/` includes:

- `schema_version`, `spec_id`, `spec_version`, `run_id`, `test_type`;
- `baseline_ref`, `head_ref`, timestamps, and relevant tool/runtime versions;
- per-gate command, status, exit code, duration, summary, and evidence references;
- baseline/new/resolved finding counts when ratcheting;
- final `GREEN`, `YELLOW`, `RED`, or `BLOCKED` decision and blocking IDs.

The template is `tests/_template/quality-gate-result.template.json`. Results MUST NOT be fabricated for planning-only work.
