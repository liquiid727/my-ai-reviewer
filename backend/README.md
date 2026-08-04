# Backend

The backend is a FastAPI modular monolith with a separate Celery worker process. The stable architecture source is [`design/backend-architecture.md`](../design/backend-architecture.md); the system-level view is [`design/architecture.md`](../design/architecture.md).

**Runtime:** Python 3.12+ (`requires-python = ">=3.12"` in `pyproject.toml`; Ruff `target-version = "py312"`, mypy `python_version = "3.12"`).

## Local Entry Points

- API application: `backend.main:app`
- Celery application: `backend.celery_app:celery`
- API router: `backend.api.v1.router:api_router`
- Database migrations: `infra/alembic/`
- Quality gates (repo root): `make ci-fast` / `make ci` — shared runners in `scripts/quality/` (see `rules/quality-gates.md`)

## Package Map

```text
backend/
  api/            HTTP routes and transport schemas
  application/    use cases and orchestration
  domain/         business rules and data contracts
  workflow/       LangGraph interview graph and nodes
  agents/         LLM-facing interview capabilities
  infrastructure/ database, storage, parsers, LLM, rendering, privacy
  tasks/          Celery task entry points and pipelines
  tests/          unit, integration, and end-to-end test areas
```

For feature behavior, follow the linked `specs/` directory and the relevant issue acceptance file. Do not treat the empty `rag/`, `memory/`, `multimodal/`, or `sandbox/` packages as active services without a feature implementation and tests.
