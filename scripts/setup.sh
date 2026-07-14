#!/usr/bin/env bash
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERR]${NC}  $*"; }

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "============================================="
echo "  AI Interview Platform — Quick Setup"
echo "============================================="
echo ""

# ── 1. Check prerequisites ──────────────────────
info "Checking prerequisites..."

MISSING=()
command -v docker  >/dev/null 2>&1 || MISSING+=("docker")
command -v uv      >/dev/null 2>&1 || MISSING+=("uv (https://docs.astral.sh/uv/)")
command -v pnpm    >/dev/null 2>&1 || MISSING+=("pnpm (https://pnpm.io/installation)")
command -v python3 >/dev/null 2>&1 || MISSING+=("python3 (>=3.11)")

if [ ${#MISSING[@]} -gt 0 ]; then
    err "Missing tools:"
    for tool in "${MISSING[@]}"; do
        echo "   - $tool"
    done
    echo ""
    echo "Install them first, then re-run this script."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    err "Python >= 3.11 required, found $PY_VERSION"
    exit 1
fi

ok "All prerequisites found (Python $PY_VERSION)"

# ── 2. Create .env from example ─────────────────
if [ ! -f .env ]; then
    info "Creating .env from .env.example..."
    cp .env.example .env

    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || true)
    if [ -n "$ENCRYPTION_KEY" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$ENCRYPTION_KEY|" .env
        else
            sed -i "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$ENCRYPTION_KEY|" .env
        fi
        ok "Generated ENCRYPTION_KEY"
    else
        warn "Could not auto-generate ENCRYPTION_KEY — set it manually in .env"
    fi

    warn "Edit .env to add your LLM API key (OPENAI_API_KEY or ANTHROPIC_API_KEY)"
else
    ok ".env already exists, skipping"
fi

# ── 3. Start infrastructure ─────────────────────
info "Starting Docker infrastructure (Postgres + Redis + MinIO)..."
docker compose up -d
ok "Infrastructure containers started"

info "Waiting for services to be healthy..."
TIMEOUT=60
ELAPSED=0
while ! docker compose ps --format json 2>/dev/null | python3 -c "
import sys, json
lines = sys.stdin.read().strip().split('\n')
services = [json.loads(l) for l in lines if l.strip()]
infra = [s for s in services if s.get('Service') != 'minio-init']
healthy = all(s.get('Health','') == 'healthy' for s in infra if s.get('Health'))
sys.exit(0 if healthy else 1)
" 2>/dev/null; do
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    if [ $ELAPSED -ge $TIMEOUT ]; then
        warn "Timed out waiting for healthy containers — continuing anyway"
        break
    fi
done
ok "Infrastructure ready"

# ── 4. Install backend dependencies ─────────────
info "Installing backend dependencies..."
cd "$PROJECT_ROOT/backend"
uv sync
ok "Backend dependencies installed"

# ── 5. Run database migrations ───────────────────
info "Running database migrations..."
cd "$PROJECT_ROOT"
cd backend && uv run alembic -c ../alembic.ini upgrade head
ok "Database migrations complete"

# ── 6. Install frontend dependencies ────────────
info "Installing frontend dependencies..."
cd "$PROJECT_ROOT/frontend"
pnpm install
ok "Frontend dependencies installed"

# ── 7. Summary ──────────────────────────────────
cd "$PROJECT_ROOT"
echo ""
echo "============================================="
echo -e "${GREEN}  Setup complete!${NC}"
echo "============================================="
echo ""
echo "  Before starting, make sure to:"
echo -e "  ${YELLOW}1. Edit .env and set your LLM API key${NC}"
echo "     OPENAI_API_KEY=sk-... (for OpenAI/DeepSeek)"
echo "     or ANTHROPIC_API_KEY=... (for Claude)"
echo ""
echo "  Quick start commands:"
echo "  ─────────────────────────────────────────"
echo "  make dev          # Start everything (infra + backend + frontend)"
echo ""
echo "  Or start individually:"
echo "  make infra        # Docker containers only"
echo "  make backend      # FastAPI on :8000"
echo "  make backend-worker  # Celery worker"
echo "  make frontend     # Vite on :5173"
echo ""
echo "  URLs:"
echo "  Frontend:   http://localhost:5173"
echo "  Backend:    http://localhost:8000/docs"
echo "  MinIO:      http://localhost:9001 (minioadmin/minioadmin)"
echo ""
