#!/usr/bin/env bash
# Gate: make type-check
# backend mypy (strict, with config-file) + frontend tsc
# Read-only: never mutates source.

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

# CRITICAL: always pass --config-file backend/pyproject.toml so mypy loads
# backend tool config when invoked from the monorepo root.
run_one "type-backend" \
  env PYTHONPATH=. uv run --project backend mypy backend \
    --config-file backend/pyproject.toml

run_one "type-frontend" \
  bash -c 'cd frontend && pnpm exec tsc -b --pretty false'

if [[ "${failed}" -ne 0 ]]; then
  qg_fail "type-check" "failed gates: ${failed_gates[*]}"
  exit 1
fi

qg_pass "type-check"
exit 0
