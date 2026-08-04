#!/usr/bin/env bash
# Gate: make test-frontend
# If frontend/package.json has no "test" script → explicit BLOCKED/FAIL non-zero.
# Do NOT silent-pass. When harness exists (issue #075), run pnpm test.
# Read-only.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

if ! frontend_has_test_script; then
  reason="frontend test harness not configured (issue #075)"
  qg_blocked "test-frontend" "${reason}"
  # Standalone make test-frontend must be non-zero until harness exists.
  exit 2
fi

if ! run_gate "test-frontend" -- bash -c 'cd frontend && pnpm test'; then
  qg_fail "test-frontend"
  exit 1
fi

qg_pass "test-frontend"
exit 0
