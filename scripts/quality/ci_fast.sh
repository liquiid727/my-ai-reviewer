#!/usr/bin/env bash
# Gate: make ci-fast
# lint + type-check + arch-check + test-unit + build
# Runs all gates, aggregates failures, exits non-zero if any fail.
# Does NOT require frontend tests or integration services.
# Read-only.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

failed=0
failed_gates=()
blocked_gates=()

run_script() {
  local gate_id="$1"
  shift
  qg_info "ci-fast → ${gate_id} ($*)"
  set +e
  "$@"
  local rc=$?
  set -e
  if [[ "${rc}" -eq 0 ]]; then
    qg_pass "${gate_id}"
  elif [[ "${rc}" -eq 2 ]]; then
    qg_blocked "${gate_id}" "exit=${rc}"
    blocked_gates+=("${gate_id}")
    failed=1
  else
    qg_fail "${gate_id}" "exit=${rc}"
    failed_gates+=("${gate_id}")
    failed=1
  fi
}

run_script "lint" bash "${SCRIPT_DIR}/lint.sh"
run_script "type-check" bash "${SCRIPT_DIR}/typecheck.sh"
run_script "arch-check" env PYTHONPATH=. uv run --project backend python "${SCRIPT_DIR}/arch_check.py"
run_script "test-unit" bash "${SCRIPT_DIR}/test_unit.sh"
run_script "build" bash "${SCRIPT_DIR}/build.sh"

if [[ "${failed}" -ne 0 ]]; then
  msg=""
  if [[ "${#failed_gates[@]}" -gt 0 ]]; then
    msg+=" failed=${failed_gates[*]}"
  fi
  if [[ "${#blocked_gates[@]}" -gt 0 ]]; then
    msg+=" blocked=${blocked_gates[*]}"
  fi
  qg_fail "ci-fast" "${msg}"
  exit 1
fi

qg_pass "ci-fast"
exit 0
