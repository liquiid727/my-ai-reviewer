# Testing And Gate Knowledge

## Gate Design

A useful gate is deterministic, read-only, locally reproducible, fast enough for its placement, explicit about prerequisites, and strict about exit status. Make and hosted CI should call the same underlying commands or scripts.

Separate gate concerns so failures are diagnosable:

- lint/format finds syntax, import, style, and obvious correctness issues;
- type checking finds contract mismatch;
- architecture checking finds dependency violations and expired exceptions;
- unit tests protect pure behavior and edge cases;
- integration/API tests protect real boundaries;
- browser/component tests protect user-visible state and interaction;
- build checks protect packaging and TypeScript bundling.

## Baseline And Ratchet

Never encode the 2026-08-04 finding counts as accepted debt. Record a machine-readable baseline by stable finding identity, reject new findings, and remove old entries through linked issues. Full zero-error gates replace the baseline as soon as it is green.

Coverage follows the same model: measure with a reproducible command, record the baseline, prevent decreases, and raise targets intentionally. Requirement mapping and critical branch tests matter more than a high aggregate number.

## Skip And Blocker Semantics

- A test intentionally excluded by scope is `NOT_RUN` and needs rationale.
- A test that cannot start because PostgreSQL/Redis/MinIO/browser is unavailable is `BLOCKED`.
- A test that starts and fails setup due to a product/config defect is `FAIL`.
- A pytest skip caused by missing required infrastructure is not passing integration evidence.
- Optional dependency behavior needs both installed and unavailable-path tests when the feature contract supports both.

## Required Test Shape

Map each acceptance criterion to one or more of:

- pure unit behavior;
- adapter contract;
- API success/validation/not-found/conflict/dependency error;
- retry, timeout, expiry, concurrency, run/revision ownership;
- UI loading/empty/success/failure/pending/conflict;
- privacy fail-closed and no-PII evidence;
- migration upgrade/downgrade and compatibility.

Store exact commands and artifacts. Do not create standardized result files for commands that were never run.

## Gate Review Traps

- Verification targets that run formatters or `--fix` mutate evidence.
- One aggregate shell pipeline hides which check failed.
- Separate Make/CI command copies drift over time.
- Broad `ignore-missing-imports`, lint exclusions, test skips, or architecture allowlists can hide new debt.
- A passing frontend build does not replace component or browser behavior tests.
- A mocked adapter unit test does not replace one real adapter contract test.
