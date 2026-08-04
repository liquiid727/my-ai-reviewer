#!/usr/bin/env bash
# Gate: make lint
# backend ruff check + ruff format --check + frontend oxlint
# Read-only: never auto-fixes source, never mutates files.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

failed=0
failed_gates=()

run_one() {
  local gate_id="$1"
  shift
  if ! run_gate "${gate_id}" -- "$@"; then
    failed=1
    failed_gates+=("${gate_id}")
  fi
}

run_one "lint-backend" \
  env PYTHONPATH=. uv run --project backend ruff check backend

run_one "format-backend" \
  env PYTHONPATH=. uv run --project backend ruff format --check backend

run_one "lint-frontend" \
  bash -c 'cd frontend && pnpm lint'

if [[ "${failed}" -ne 0 ]]; then
  qg_fail "lint" "failed gates: ${failed_gates[*]}"
  exit 1
fi

qg_pass "lint"
exit 0
