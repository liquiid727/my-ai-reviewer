# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Monorepo for an **AI Interview / Resume Intelligence Platform**: FastAPI modular monolith + React SPA + Celery workers. Long-term vision is a full Agent Interview stack (RAG, memory, multimodal, sandbox, SaaS); current runtime is resume intelligence, privacy-gated LLM processing, JD library/matching, job-search plans, resume builder, and a LangGraph interview loop.

Stable design lives in `design/`. Feature behavior lives in `specs/<SPEC-ID>-<slug>/`. Live delivery state lives in `current/`. Prefer those over this file when they disagree.

## Before starting work

Load context in this order (token-efficient):

1. `README.md`
2. `current/project-status.md`, `current/active-feature.md`, `current/active-tasks.md`
3. Relevant `design/*.md` (architecture / backend / frontend / database / api-guidelines / coding-guidelines)
4. Active feature under `specs/<SPEC-ID>-*/` (`spec.md`, `tasks.md`, issue acceptance)
5. Role skill under `.agents/` (`backend`, `frontend`, `testing`, `ci`, `prompt`, `review`)

SpecOS rules (`AGENTS.md`): preserve human-authored drafts; keep generated artifacts traceable; cover empty/loading/success/failure for user-facing flows; record assumptions when requirements are ambiguous.

## Common commands

Root `Makefile` is the preferred entry point. Package managers: **uv** (backend), **pnpm** (frontend).

```bash
# First-time / deps
make setup                          # scripts/setup.sh
make install                        # backend uv sync + frontend pnpm install
cp .env.example .env                # fill ENCRYPTION_KEY, PRIVACY_QUARANTINE_KEY, LLM keys

# Infra (Postgres :5433, Redis :6379, MinIO :9000/:9001)
make infra                          # docker compose up -d
make infra-down
make db-migrate                     # alembic -c alembic.ini upgrade head (migrations in infra/alembic/)

# Full stack
make hot                            # or make dev — infra + API reload + Celery + Vite HMR
make start                          # production-ish: build frontend + preview
make backend-up                     # infra + API reload + worker
make frontend-up                    # Vite only (/api → :8000)
make stop

# Individual processes (from repo root; PYTHONPATH=.)
make hot-backend                    # uvicorn backend.main:app --reload :8000
make start-worker                   # celery -A backend.celery_app:celery worker
make hot-frontend                   # pnpm dev :5173
# Equivalent manual forms:
PYTHONPATH=. uv run --project backend uvicorn backend.main:app --reload --port 8000
PYTHONPATH=. uv run --project backend celery -A backend.celery_app:celery worker --loglevel=info
cd frontend && pnpm dev

# Lint / test
make lint                           # ruff check backend + pnpm lint (oxlint)
make test                           # pytest backend
PYTHONPATH=. uv run --project backend ruff check backend --fix
PYTHONPATH=. uv run --project backend ruff format backend
PYTHONPATH=. uv run --project backend mypy backend
PYTHONPATH=. uv run --project backend pytest backend/tests/unit -v
PYTHONPATH=. uv run --project backend pytest backend/tests/unit/test_parsers.py -v
PYTHONPATH=. uv run --project backend pytest backend/tests/integration -v
cd frontend && pnpm lint && pnpm build
```

Health: `GET /api/health`. API base: `/api/v1`. Default DB URL: `postgresql+asyncpg://postgres:postgres@localhost:5433/ai_interview`.

Optional imaging extras (photo beautify): `cd backend && uv sync --extra imaging` (otherwise photo APIs may return 501).

## High-level architecture

```text
Browser (React 19 + Vite SPA)
  |  /api proxy → localhost:8000 in dev
  v
FastAPI (backend/main.py)
  api/v1 → application services → domain + infrastructure
  |                |
  PostgreSQL    MinIO (resumes / quarantine / photos / exports)
  |
  Redis → Celery worker (resume, JD, plan, interview report pipelines)
  |
  LLMGateway → OpenAI-compatible / Anthropic  (+ PrivacyGuard on sensitive paths)
```

Modular monolith, not microservices. Empty packages `backend/rag/`, `memory/`, `multimodal/`, `sandbox/`, `evaluation/` are extension scaffolds — do not treat as live services without a feature spec + implementation + tests.

### Backend layering (DDD-inspired)

| Package | Role | Depends on |
|---|---|---|
| `backend/api/v1/` | HTTP, validation, `APIResponse` envelope | application, domain schemas |
| `backend/application/` | Use cases, transactions, status machines, Celery dispatch | domain, infrastructure |
| `backend/domain/` | Entities, enums, pure rules/schemas | stdlib + Pydantic only |
| `backend/infrastructure/` | DB, MinIO, parsers, LLM, privacy, rendering, imaging, web fetch | external SDKs |
| `backend/workflow/` | LangGraph interview graph, nodes, checkpointer | agents, domain, LLM |
| `backend/agents/` | Question / evaluation / followup / report (structured LLM I/O) | LLM gateway |
| `backend/tasks/` | Thin Celery entrypoints + pipeline stages | application/domain/infra |

**Rules for new code**

- API handlers do not own multi-step business logic or call provider SDKs.
- Domain must stay free of FastAPI / Celery / MinIO / provider SDKs.
- Celery tasks load state → call a use case → persist terminal/intermediate status; retries use resource/run IDs.
- LangGraph nodes do one operation and return **partial** state dicts (never silently replace full state).
- Schema changes require Alembic under `infra/alembic/` and an update to `design/database.md` when relationships/states change.
- Reality check: some services still import SQLAlchemy models directly; move toward application-owned use cases without inventing speculative ports.

### Feature modules (as-built)

| Feature | API | Notes |
|---|---|---|
| Resume + privacy | `api/v1/resume.py` | Upload → encrypted quarantine → local mask → optional privacy review → masked extract/classify/evaluate. States include `privacy_scanning`, `privacy_review_required`, `text_masked`, `fact_extracted`, `classified`, `evaluated`, `failed`. |
| Interview | `api/v1/interview.py` | LangGraph Q&A loop with interrupt/resume; report via Celery |
| JD library | `api/v1/jd.py` | text/file/URL import, extract, match (not full vector RAG yet) |
| Job-search plans | `api/v1/plans.py` | Async generation; run/revision guards on regenerate/mutate |
| Resume builder | `api/v1/resume_builder.py` | Drafts, AI proposals (allow-listed ops), PDF preview/export, photos |
| LLM settings | `api/v1/settings.py` | Encrypted API keys; verified config hard-gates protected flows |

LLM entrypoint: `backend/infrastructure/llm/gateway.py`. Prompts under `infrastructure/llm/prompts/`. Always System + User separation and Pydantic structured outputs for agent results.

### Privacy boundary (critical)

Resume-derived data must not reach providers in cleartext:

1. Upload encrypted into short-lived MinIO quarantine bucket.
2. Local redaction → placeholders + masked text + manifest (risk flags, policy version, revision, TTL).
3. `PrivacyGuard` fails closed if identifiers leak into an LLM payload.
4. Approval deletes quarantine object and starts masked pipeline.
5. Builder/export rehydration only replaces **manifest-declared exact tokens**.

Keys: `ENCRYPTION_KEY`, `PRIVACY_QUARANTINE_KEY` (see `.env.example`).

### Frontend structure

- Routes: `frontend/src/App.tsx` (source of truth).
- API: `src/api/*.ts` via `api/client.ts` (`BASE_URL=/api/v1`, `ApiRequestError` on non-2xx).
- Cross-page state: Zustand (`resumeStore`, `resumeHistoryStore`, `interviewStore`, `settingsStore`). No React Query — mutations that affect other routes must explicitly refresh.
- UI: Tailwind 4 + Radix primitives in `components/ui/`; neobrutalist borders/shadows; copy via i18next (`src/i18n/`, zh + en).
- Every data-backed page must handle loading / empty / success / failure (and revision/TTL conflicts for builder, plans, privacy).
- Builder is full-bleed; other routes use the shared `Layout` shell.
- Binary PDF export and assistant proposal errors use specialized fetch paths — keep those exceptions inside the builder API module.

### API conventions

- Envelope: `{"code": 0, "message": "...", "data": {...}}` (`code=0` success). Binary exports are the exception.
- Error codes in use/docs: `1001` param, `1002` not found, `1003` bad state, `5001` LLM failure, `5002` agent timeout.
- No auth/tenant middleware yet — local single-user dev assumption. Do not pretend multi-tenant safety exists.

## Testing notes

- Unit: `backend/tests/unit/` — domain, parsers, privacy, LLM adapters, services (mock LLM).
- Integration: `backend/tests/integration/` — API + DB (needs Compose infra).
- `pytest-asyncio` mode `auto` (see `backend/pyproject.toml`).
- Mock at the gateway/agent boundary; do not hit real providers in unit tests.
- Frontend: `pnpm lint` / `pnpm build` (tsc + vite). No large FE unit suite assumed.

## Known gaps (do not “fix” casually)

- No authentication, ownership checks, or rate limiting.
- Qdrant / hybrid RAG / embeddings / rerank are design targets only.
- OpenTelemetry / LangSmith not fully wired.
- `current/*` and some skill paths may lag code; trust `design/*` as-built docs + the code when status files are stale.
- Repo-wide mypy may already be red from pre-existing errors — fix what you touch; don’t expand the blast radius without intent.

## Reference index

| Path | Use |
|---|---|
| `design/architecture.md` | System baseline |
| `design/backend-architecture.md` | Backend packages, APIs, workers |
| `design/frontend-architecture.md` | Routes, stores, UI contracts |
| `design/database.md` | Tables / relationships |
| `design/api-guidelines.md` | REST + flow vocabulary |
| `design/coding-guidelines.md` | Layering + LangGraph node style |
| `specs/roadmap.md` | Epic roadmap (AIP + RIP) |
| `specs/RIP-*`, `specs/AIP-*` | Feature specs |
| `.agents/*.skill.md` | Role playbooks |
| `infra/alembic/` | Migrations |
| `tasks/`, `reviews/`, `tests/` | Delivery / evidence chain |
