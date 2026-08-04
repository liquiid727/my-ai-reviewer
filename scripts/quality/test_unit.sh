#!/usr/bin/env bash
# Gate: make test-unit
# backend unit pytest; frontend unit only if package.json has a test script.
# Read-only.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

failed=0
failed_gates=()

if ! run_gate "test-backend-unit" -- \
  env PYTHONPATH=. uv run --project backend pytest backend/tests/unit -q; then
  failed=1
  failed_gates+=("test-backend-unit")
fi

if frontend_has_test_script; then
  if ! run_gate "test-frontend-unit" -- \
    bash -c 'cd frontend && pnpm test'; then
    failed=1
    failed_gates+=("test-frontend-unit")
  fi
else
  qg_not_run "test-frontend-unit" "frontend test harness not configured (issue #075)"
fi

if [[ "${failed}" -ne 0 ]]; then
  qg_fail "test-unit" "failed gates: ${failed_gates[*]}"
  exit 1
fi

qg_pass "test-unit"
exit 0
