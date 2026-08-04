#!/usr/bin/env bash
# Shared helpers for quality gate runners.
# Read-only: never mutates source, never auto-fixes.

set -euo pipefail

# Resolve repository root (scripts/quality -> scripts -> root).
quality_root() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "${here}/../.." && pwd
}

REPO_ROOT="$(quality_root)"
cd "${REPO_ROOT}"

# Optional colors (disabled when not a TTY or NO_COLOR is set).
if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  QG_RED=$'\033[1;31m'
  QG_GREEN=$'\033[1;32m'
  QG_YELLOW=$'\033[1;33m'
  QG_CYAN=$'\033[1;36m'
  QG_RESET=$'\033[0m'
else
  QG_RED=""
  QG_GREEN=""
  QG_YELLOW=""
  QG_CYAN=""
  QG_RESET=""
fi

qg_info() {
  printf '%s==> %s%s\n' "${QG_CYAN}" "$*" "${QG_RESET}"
}

qg_pass() {
  local gate_id="$1"
  shift || true
  printf '%sPASS%s [%s]%s\n' "${QG_GREEN}" "${QG_RESET}" "${gate_id}" "${1:+ $*}"
}

qg_fail() {
  local gate_id="$1"
  shift || true
  printf '%sFAIL%s [%s]%s\n' "${QG_RED}" "${QG_RESET}" "${gate_id}" "${1:+ $*}" >&2
}

qg_blocked() {
  local gate_id="$1"
  shift || true
  printf '%sBLOCKED%s [%s]%s\n' "${QG_YELLOW}" "${QG_RESET}" "${gate_id}" "${1:+ $*}" >&2
}

qg_not_run() {
  local gate_id="$1"
  shift || true
  printf 'NOT_RUN [%s]%s\n' "${gate_id}" "${1:+ $*}"
}

# Run a named gate command. Prints gate id + exact command.
# Preserves underlying exit code. Never hides stderr.
# Usage: run_gate GATE_ID -- command args...
run_gate() {
  local gate_id="$1"
  shift
  if [[ "${1:-}" == "--" ]]; then
    shift
  fi
  if [[ "$#" -eq 0 ]]; then
    qg_fail "${gate_id}" "no command provided"
    return 1
  fi

  local cmd_display
  cmd_display="$*"
  qg_info "[${gate_id}] ${cmd_display}"

  set +e
  "$@"
  local rc=$?
  set -e

  if [[ "${rc}" -eq 0 ]]; then
    qg_pass "${gate_id}"
  else
    qg_fail "${gate_id}" "exit=${rc}"
  fi
  return "${rc}"
}

# frontend_has_test_script: exit 0 if frontend/package.json has a "test" script.
frontend_has_test_script() {
  local pkg="${REPO_ROOT}/frontend/package.json"
  if [[ ! -f "${pkg}" ]]; then
    return 1
  fi
  python3 - "${pkg}" <<'PY'
import json, sys
pkg = json.load(open(sys.argv[1], encoding="utf-8"))
scripts = pkg.get("scripts") or {}
sys.exit(0 if isinstance(scripts.get("test"), str) and scripts["test"].strip() else 1)
PY
}
