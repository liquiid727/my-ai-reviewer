# Backend Architecture

**Status**: Active as-built baseline

**Last Updated**: 2026-08-05

**Runtime**: Python 3.12 target, FastAPI, SQLAlchemy async, Celery, PostgreSQL, Redis, and MinIO.

This document describes the backend that exists in `backend/`. It is intentionally more precise than the platform vision in `design/architecture.md`; empty scaffolding packages are called out as planned extension points instead of being presented as active services.

## 1. Architecture Style

The backend is a DDD-inspired modular monolith with asynchronous I/O and a separate Celery worker process.

```text
backend/main.py
  |
  +-- FastAPI middleware and exception handlers
  +-- backend/api/v1/router.py
        |
        +-- transport routers and Pydantic request/response models
        +-- application services and use-case orchestration
        +-- domain entities, enums, schemas, and pure business rules
        +-- infrastructure adapters
              |
              +-- SQLAlchemy / PostgreSQL
              +-- MinIO storage
              +-- parsers, extractors, classifiers, evaluators
              +-- LLM providers and privacy guard
              +-- rendering, imaging, and safe web fetching

Redis -> Celery tasks -> application/domain/infrastructure -> PostgreSQL/MinIO/LLM
```

This is not a strict ports-and-adapters implementation yet. Some application services and workflow nodes import SQLAlchemy models or infrastructure adapters directly. The intended direction is to keep those imports behind application-owned use cases and stable domain contracts while avoiding speculative abstractions.

## 2. Package Responsibilities

| Package | Responsibility | May depend on |
|---|---|---|
| `backend/main.py` | Create the FastAPI app, configure CORS, include API router, expose health check, map known exceptions | API, config, domain exceptions |
| `backend/api/v1/` | HTTP routes, request validation, response serialization, resource-level error mapping | Application, domain schemas/enums, database dependency |
| `backend/application/` | Use cases, transaction orchestration, status transitions, dispatch decisions | Domain, infrastructure adapters, SQLAlchemy session |
| `backend/domain/` | Business entities, schemas, enums, pure transformations, validation, editor operations | Standard library and Pydantic; should not depend on HTTP |
| `backend/workflow/` | LangGraph state, graph topology, interrupt/resume behavior, interview nodes | Domain concepts, agents, LLM gateway, persistence for checkpoints/results |
| `backend/agents/` | Prompt-facing capabilities such as question generation, answer evaluation, follow-up, report generation | LLM gateway and domain contracts |
| `backend/infrastructure/` | Database, storage, parsers, LLM providers, rendering, web fetch, privacy quarantine, image processing | External libraries and configured services |
| `backend/tasks/` | Celery entry points and pipeline stage composition | Application/domain/infrastructure |
| `backend/infrastructure/db/` | Async engine/session, ORM models, repository helpers | PostgreSQL and SQLAlchemy |
| `infra/alembic/` | Versioned schema migrations | Database metadata and Alembic |
| `backend/tests/` | Unit, integration, and end-to-end verification of backend contracts | Application runtime and test fixtures |

## 3. Dependency Rules

The practical dependency direction is:

```text
API -> Application -> Domain
                 \-> Infrastructure
Workflow -> Agents -> LLM gateway -> Provider
Tasks -> Application / Domain / Infrastructure
Infrastructure DB -> Domain data shapes where needed
```

Rules for new code:

- API handlers should not implement multi-step business flows or call provider SDKs.
- Application services own transaction boundaries, resource existence checks, and orchestration across domains.
- Domain modules should remain usable without FastAPI, Celery, MinIO, or a provider SDK.
- Infrastructure adapters hide SDK-specific details and expose typed results or domain errors.
- Celery task functions are thin process boundaries. They should load state, call a use case, persist a terminal/intermediate status, and make retry behavior explicit.
- Celery database tasks use the dedicated `celery_database.py` `NullPool` session factory and the shared `tasks.async_runtime.run_async` bridge. This keeps asyncpg connections from crossing event loops or prefork boundaries; the web API retains the pooled engine in `database.py`.
- LangGraph nodes do one meaningful operation and return partial state updates; they must not silently replace the complete graph state.

### 3.1 Celery async runtime and database ownership

Celery uses the default prefork worker in local development. Synchronous task entry points must call `backend.tasks.async_runtime.run_async()`; they must not call `asyncio.run()`, create a module-local event loop, or keep a loop in an individual task module. The runner owns exactly one event loop per worker child process, identified by the child PID, so all async SQLAlchemy work in that child uses the same asyncpg loop.

The `worker_process_init` signal disposes the inherited SQLAlchemy pool with `close=False` after fork. The child then creates its own connections on its own loop. The `worker_process_shutdown` signal disposes async connections on that same loop before closing it. This keeps the normal pooled engine while preventing parent-process connections or connections created by another loop from crossing the worker boundary. A different Celery execution pool requires an explicit lifecycle design and must not bypass this rule.

## 4. Feature Modules

### 4.1 Resume intelligence and privacy

| Layer | Current code |
|---|---|
| API | `backend/api/v1/resume.py` |
| Application | `backend/application/resume_service/` |
| Domain | `backend/domain/resume/`, `backend/domain/privacy/` |
| Infrastructure | `parsers/`, `extractors/`, `classifiers/`, `evaluators/`, `privacy/`, `storage/` |
| Worker | `backend/tasks/resume_tasks.py` |
| Persistence | `resumes`, `files`, `resume_privacy_manifests`, `resume_sections`, `resume_facts`, `candidate_profiles`, `resume_evaluations` |

The upload path validates the file, encrypts it into the short-lived quarantine bucket, records the manifest, and dispatches processing. Local redaction creates placeholders and risk flags. When review is required, the browser can add revision-checked masks and approve only after a final `PrivacyGuard` scan. The masked pipeline then extracts text, calls the LLM for facts/profile data, classifies skills, and evaluates the resume.

The important resume state values are `uploaded`, `privacy_scanning`, `privacy_review_required`, `text_masked`, `llm_parsing`, `fact_extracted`, `classified`, `evaluating`, `evaluated`, and `failed`. `text_masked` is the approved masked handoff, while `llm_parsing` and `evaluating` make active LLM work observable. Each dispatch carries a `processing_run_id`; stale workers exit without writes. Worker events use the `resume.stage.*` and `resume.llm.*` envelopes with resource/run/task/step/attempt/error-code/duration fields and never include prompt or resume content. The exact transition logic is owned by the resume service and task pipeline; feature specs under `specs/RIP-001-*` and `specs/RIP-009-*` define acceptance behavior.

#### Processing ownership and convergence

`resume_processing_runs` is the durable execution ledger. Upload, privacy approval, retry, and reparse each create or activate a run with a unique active owner for that resume. A run records its current step, Celery task ID, attempt, last progress, deadline, terminal status, retryability, and safe error code. `resumes.processing_run_id` is only a fast current-owner pointer; all worker writes still verify the run row under a row lock.

Every stage has a deadline. Provider calls have both SDK and gateway-level timeouts, and LLM tasks have bounded soft/hard limits with at most two transient retries. Broker handoff failures are persisted as failed runs. Celery Beat reconciles overdue queued/running runs every 30 seconds, and the status endpoint performs the same lazy reconciliation for a single resume. Expired work is never silently requeued: the user must explicitly retry, while an old worker becomes a no-op if a newer run owns the resume.

### 4.2 Interview workflow

| Layer | Current code |
|---|---|
| API | `backend/api/v1/interview.py` |
| Application | `backend/application/interview_service.py` |
| Workflow | `backend/workflow/graphs/interview_graph.py`, `workflow/nodes/` |
| Agents | `backend/agents/question_agent/`, `evaluation_agent/`, `followup_agent/`, `report_agent/` |
| Worker | `backend/tasks/interview_tasks.py` for final report generation |
| Persistence | `interviews`, `interview_questions`, `question_answers`, `interview_reports` |

The graph loads the parsed resume, generates questions, interrupts for the browser's answer, evaluates the answer, optionally creates up to the configured follow-up rounds, and either presents the next question or finishes. LangGraph checkpointing uses a thread ID derived from the interview ID. Finishing the graph updates the interview status and dispatches report generation to Celery.

### 4.3 JD library and matching

| Layer | Current code |
|---|---|
| API | `backend/api/v1/jd.py` |
| Application | `backend/application/jd_import_service.py` |
| Domain | `backend/domain/jd/` |
| Infrastructure | `safe_fetcher.py`, parsers, `jd_extractor.py`, LLM gateway |
| Worker | `backend/tasks/jd_tasks.py` |
| Persistence | `job_descriptions`, `jd_match_results`, and source file metadata |

Text, file, and URL sources enter one import service. The worker pipeline extracts source text, checks duplicates, calls structured LLM extraction, and records a `ready` or `failed` state. Matching is a domain service over the normalized JD and candidate profile; it is not yet the vector retrieval pipeline shown in the architecture image.

### 4.4 Job-search plans

| Layer | Current code |
|---|---|
| API | `backend/api/v1/plans.py` |
| Application | `plan_service.py`, `plan_task_service.py`, `plan_regeneration_service.py` |
| Domain | `backend/domain/job_search_plan/` |
| Infrastructure | `backend/infrastructure/planners/llm_plan_generator.py` |
| Worker | `backend/tasks/plan_tasks.py` |
| Persistence | `job_search_plans`, `job_search_plan_tasks` |

Plan generation is asynchronous. Initial generation and regeneration carry a run ID; mutations carry a revision. Unfinished plans and manual tasks are protected from unsafe replacement during regeneration. The API exposes list/detail, retry, regenerate, task CRUD, reorder, patch, and delete operations.

### 4.5 Resume Builder

The Builder creates a draft from a candidate profile or a reference template, stores editable content and design tokens as JSONB, and renders preview/export PDFs through infrastructure renderers. Draft updates use revisions; AI assistant output is a constrained proposal of allow-listed operations and must be explicitly applied. Photo upload is processed separately and only confirmed object references are written into draft content.

Relevant code:

- API: `backend/api/v1/resume_builder.py`
- Domain: `backend/domain/resume_builder/`
- Application: `backend/application/resume_edit_service.py`
- Infrastructure: `rendering/`, `imaging/`, `editors/`, `polishers/`, `evaluators/`
- Persistence: `resume_drafts`, edit sessions/proposals/messages, photo metadata

### 4.6 LLM settings

`backend/api/v1/settings.py` and `backend/application/llm_config_service.py` manage provider/model configuration. API keys are encrypted before persistence. The LLM gate requires an active verified configuration for protected flows. `LLMGateway` resolves database configuration or environment configuration, delegates to a provider adapter, and can apply `PrivacyGuard` before and after a privacy-sensitive call.

## 5. Representative API Surface

All feature routes are mounted below `/api/v1` and return the shared `APIResponse` envelope unless the route explicitly returns a binary export.

| Resource | Representative endpoints | Use |
|---|---|---|
| Resume | `POST /resume/upload`, `GET /resume`, `GET /resume/{id}`, `GET /resume/{id}/status`, `GET/POST /resume/{id}/privacy/*`, `GET /resume/{id}/facts`, `GET /resume/{id}/profile`, `POST /resume/{id}/retry`, `POST /resume/{id}/reparse` | Upload, privacy review, processing status, parsed output, retry |
| Interview | `POST /interview/create`, `POST /interview/{id}/start`, `POST /interview/{id}/answer`, `GET /interview/{id}/status`, `GET /interview/{id}/report` | Interactive LangGraph interview |
| JD | `POST /jd/import/{text,file,url}`, `GET /jd`, `GET /jd/{id}`, `PATCH /jd/{id}`, `POST /jd/match`, `POST /jd/{id}/retry`, `POST /jd/{id}/reextract` | JD ingestion, extraction, matching |
| Plans | `POST /plans`, `GET /plans`, `GET/PATCH/DELETE /plans/{id}`, `POST /plans/{id}/retry`, `POST /plans/{id}/regenerate`, task CRUD/order routes | Job-search planning |
| Builder | `GET /builder/templates`, `GET /builder/drafts`, `POST /builder/from-*`, `GET/PUT/DELETE /builder/{id}`, assistant/proposal routes, preview/export/photo routes | Resume drafting, AI editing, PDF output |
| Settings | `GET/POST /settings/llm`, `PUT/DELETE /settings/llm/{id}`, `POST /settings/llm/test` | Provider configuration and verification |

The route files are the exhaustive contract source for paths and request models. Feature specs under `specs/` own behavior that is too detailed for this stable overview.

## 6. Data and Storage

`design/database.md` is the canonical relationship document. Backend changes should update it when they add a stable entity, relationship, state, or data retention rule.

| Data | Store | Notes |
|---|---|---|
| Resource and workflow state | PostgreSQL | SQLAlchemy async sessions and Alembic migrations |
| Short-lived queue/result state | Redis | Celery broker and result backend |
| Quarantined resume source | MinIO encrypted quarantine bucket | TTL and explicit deletion after privacy approval/expiry |
| Durable/generated files | MinIO resume, photo, and export buckets | Database stores metadata/object references |
| LangGraph checkpoints | PostgreSQL checkpointer integration | Thread ID is tied to an interview |
| LLM configuration secret | PostgreSQL encrypted field | Plain API keys are not returned in API responses |

## 7. Error and Retry Model

- Transport validation is handled by FastAPI/Pydantic.
- Known domain failures are translated to response codes/messages in the router or global handlers.
- Pipeline failures persist a `failed` state, a stable allow-listed `error_code`, and a safe message suitable for retry or user display; provider payloads and exception text are not persisted.
- Celery jobs use resource IDs and run IDs so retries target an existing resource rather than creating an untracked duplicate. Each task has a hard/soft limit and stale ownership checks; overdue runs converge through Beat or a status read and require manual retry.
- Plan and Builder mutations use revision checks and return conflict behavior when the browser edits stale state.
- Privacy expiry removes the quarantine object and prevents later approval of an expired review.

The API does not yet have one global exception middleware for every domain error. New endpoints should use stable error codes and avoid leaking provider, secret, or raw quarantined-content details.

## 8. Testing Strategy

| Test layer | Location | Purpose |
|---|---|---|
| Unit | `backend/tests/unit/` | Domain rules, parsers, privacy redaction/guard, LLM adapters, rendering, services |
| Integration | `backend/tests/integration/` | API contracts, database behavior, interview and JD/plan flows |
| E2E placeholder | `backend/tests/e2e/` | Reserved for full backend workflow verification |
| Migration/runtime | `tests/` and feature-specific evidence | Delivery-level acceptance and regression records |

Backend changes should include the narrowest useful unit/integration coverage and preserve empty, loading, success, and failure behavior in the consuming frontend spec.

## 9. Known Gaps and Assumptions

- Authentication, authorization, tenant ownership checks, and rate limiting are not active backend boundaries.
- `Qdrant`, hybrid retrieval, embeddings, reranking, and question-bank ingestion are design targets, not current backend services.
- Full OpenTelemetry/LangSmith trace propagation is not wired across all API and worker calls.
- `backend/rag/`, `backend/memory/`, `backend/multimodal/`, and `backend/sandbox/` contain extension points or placeholders; new features must not assume they are operational.
- The effective local database port is configuration-driven and may differ from the Compose host port. Use the active `.env.example`, `backend/config.py`, and `docker-compose.yml` together when changing local setup.
- The current API is a local development surface; production deployment needs auth, object access control, secret management, and a defined retention policy.
