#!/usr/bin/env bash
# Gate: make ci
# ci-fast + test-integration (+ test-frontend only if harness exists).
# Integration BLOCKED still fails ci.
# Missing FE harness → NOT_RUN, does not fail ci solely on FE tests absent.
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
  qg_info "ci → ${gate_id} ($*)"
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

run_script "ci-fast" bash "${SCRIPT_DIR}/ci_fast.sh"
run_script "test-integration" bash "${SCRIPT_DIR}/test_integration.sh"

# Frontend tests: only required when harness exists; otherwise NOT_RUN and continue.
if frontend_has_test_script; then
  run_script "test-frontend" bash "${SCRIPT_DIR}/test_frontend.sh"
else
  qg_not_run "test-frontend" "frontend test harness not configured (issue #075); skipping in make ci"
fi

if [[ "${failed}" -ne 0 ]]; then
  msg=""
  if [[ "${#failed_gates[@]}" -gt 0 ]]; then
    msg+=" failed=${failed_gates[*]}"
  fi
  if [[ "${#blocked_gates[@]}" -gt 0 ]]; then
    msg+=" blocked=${blocked_gates[*]}"
  fi
  qg_fail "ci" "${msg}"
  # Prefer exit 2 when only blockers (env), else 1 for behavioral fails.
  if [[ "${#failed_gates[@]}" -eq 0 && "${#blocked_gates[@]}" -gt 0 ]]; then
    exit 2
  fi
  exit 1
fi

qg_pass "ci"
exit 0
