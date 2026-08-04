#!/usr/bin/env bash
# Gate: make test-integration
# Probe Postgres + Redis; if unavailable → BLOCKED non-zero (never false pass).
# If available → pytest integration, preserve exit code.
# Read-only.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

PG_HOST="${QG_PG_HOST:-localhost}"
PG_PORT="${QG_PG_PORT:-5433}"
REDIS_HOST="${QG_REDIS_HOST:-localhost}"
REDIS_PORT="${QG_REDIS_PORT:-6379}"
PROBE_TIMEOUT="${QG_PROBE_TIMEOUT:-2}"

probe_tcp() {
  local host="$1"
  local port="$2"
  # Prefer bash /dev/tcp; fall back to python.
  if (echo >"/dev/tcp/${host}/${port}") >/dev/null 2>&1; then
    return 0
  fi
  python3 - "${host}" "${port}" "${PROBE_TIMEOUT}" <<'PY'
import socket, sys
host, port, timeout = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
s = socket.socket()
s.settimeout(timeout)
try:
    s.connect((host, port))
except OSError:
    sys.exit(1)
finally:
    s.close()
sys.exit(0)
PY
}

missing=()
if ! probe_tcp "${PG_HOST}" "${PG_PORT}"; then
  missing+=("Postgres ${PG_HOST}:${PG_PORT}")
fi
if ! probe_tcp "${REDIS_HOST}" "${REDIS_PORT}"; then
  missing+=("Redis ${REDIS_HOST}:${REDIS_PORT}")
fi

if [[ "${#missing[@]}" -gt 0 ]]; then
  reason="missing prerequisites: ${missing[*]}. Start with: make infra"
  qg_blocked "test-backend-integration" "${reason}"
  qg_blocked "test-integration" "${reason}"
  exit 2
fi

qg_info "prerequisites ok: Postgres ${PG_HOST}:${PG_PORT}, Redis ${REDIS_HOST}:${REDIS_PORT}"

if ! run_gate "test-backend-integration" -- \
  env PYTHONPATH=. uv run --project backend pytest backend/tests/integration -q; then
  qg_fail "test-integration"
  exit 1
fi

qg_pass "test-integration"
exit 0
