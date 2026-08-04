#!/usr/bin/env bash
# Gate: make build
# frontend production build (tsc -b && vite build via pnpm build)
# Read-only verification (build output is generated artifact, not source mutation).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

if ! run_gate "build-frontend" -- bash -c 'cd frontend && pnpm build'; then
  qg_fail "build"
  exit 1
fi

qg_pass "build"
exit 0
