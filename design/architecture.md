# System Architecture

**Status**: Active as-built baseline

**Last Updated**: 2026-08-04

**Scope**: The current architecture of the AI Interview Platform repository.

This document is the system-level entry point. Detailed implementation boundaries live in:

- `design/backend-architecture.md` - FastAPI application and worker architecture.
- `design/frontend-architecture.md` - React/Vite SPA architecture.
- `design/domain.md` - domain model and interview workflow concepts.
- `design/database.md` - relational model and migration-owned schema.
- `design/api-guidelines.md` - API conventions and business flow vocabulary.
- `design/deployment.md` - local infrastructure and operational dependencies.

## 1. Architectural Position

The repository is a monorepo containing a React single-page application and a Python modular monolith. The browser talks to the FastAPI application over HTTP. FastAPI owns request validation and use-case orchestration; domain modules hold business rules; infrastructure modules implement persistence, file handling, parsing, LLM calls, rendering, and external integrations.

Long-running work is handed to Celery workers through Redis. PostgreSQL is the source of truth for business state. MinIO stores files and generated artifacts. LLM providers are accessed through one backend gateway so provider-specific details do not leak into API or domain code.

```text
Browser
  |
  | React + Vite SPA
  | /api proxy in development
  v
FastAPI application (backend/main.py)
  |
  +-- /api/v1 router modules
  |       |
  |       +-- application services
  |       +-- domain rules and schemas
  |       +-- infrastructure adapters
  |
  +-- PostgreSQL -----------------------------+
  |                                           |
  +-- MinIO object storage                   |
  |                                           |
  +-- Redis --> Celery worker --> async jobs -+
  |                         |
  +-- LLM gateway ------------+--> OpenAI-compatible / Anthropic providers
```

This is a modular monolith, not a microservice deployment. The module boundaries are code ownership and dependency boundaries inside one backend process and one worker application.

## 2. Runtime Components

| Component | Current implementation | Responsibility |
|---|---|---|
| Web client | React 19, TypeScript, Vite | Routes, forms, workflow screens, local UI state, API calls |
| API process | FastAPI in `backend/main.py` | HTTP, CORS, `/api/health`, `/api/v1` routing, exception mapping |
| Worker process | Celery in `backend/celery_app.py` | Resume, JD, plan, interview report background work |
| Relational store | PostgreSQL through SQLAlchemy async | Business entities, workflow status, structured JSON data, revisions |
| Cache/queue | Redis | Celery broker/result backend; future session-memory use |
| Object store | MinIO | Quarantine uploads, resume files, photos, PDF exports |
| LLM gateway | `backend/infrastructure/llm/` | Provider selection, API-key decryption, privacy guard, normalized responses |
| Migrations | Alembic under `infra/alembic/` | Versioned database schema changes |

The repository also contains empty or partial directories for RAG, memory, multimodal processing, sandbox execution, and additional agents. Those directories describe the intended extension points; they are not current runtime dependencies unless a feature spec and implementation connect them to a workflow.

## 3. Current Capability Map

```text
Resume input
  upload -> encrypted quarantine -> local masking -> privacy review (when required)
  -> masked text extraction -> LLM fact/profile extraction
  -> rule classification -> LLM evaluation

Interview
  ready resume -> create interview -> LangGraph question loop
  -> answer evaluation -> optional follow-up -> next question
  -> Celery report generation

JD and job preparation
  text/file/URL import -> source extraction -> duplicate check
  -> LLM structured extraction -> JD/resume matching
  -> generated job-search plan -> editable AI/manual tasks

Resume Builder
  candidate profile or reference template -> editable draft
  -> revision-checked updates and AI proposals
  -> preview/export PDF and optional photo processing
```

The uploaded architecture image `20260723-153708.jpg` describes the larger platform direction, especially parser, extractor, embedding, vector store, retrieval, ranking, and result formatting. In the current code, parser/extractor/matching/formatting are partially or fully represented, while embedding/vector retrieval and the complete RAG ranking chain remain planned work.

## 4. Cross-Component Request Flow

### 4.1 Synchronous request

```text
Page or component
  -> frontend/src/api/client.ts
  -> /api/v1/<resource>
  -> backend/api/v1/<resource>.py
  -> application service
  -> domain validation + infrastructure adapter
  -> PostgreSQL / MinIO / LLM
  -> APIResponse envelope
  -> typed page state
```

### 4.2 Asynchronous request

```text
API endpoint
  -> persist initial state
  -> dispatch Celery task through Redis
  -> return resource ID and processing state
  -> worker executes one or more stages
  -> update PostgreSQL state
  -> frontend polls or reloads the resource
```

Workers must be safe to retry. Resume and job-search-plan pipelines use explicit status and run/revision checks so a stale worker cannot silently overwrite a newer user action.

## 5. Data and Privacy Boundaries

PostgreSQL is authoritative for resource state. JSONB is used for structured LLM output and editable document content where the shape is intentionally extensible. Files are kept out of the database and referenced by storage metadata.

Resume-derived data crosses an explicit privacy boundary:

1. The upload is encrypted before it is placed in the short-lived quarantine bucket.
2. Local redaction produces placeholders and a masked text view.
3. A manifest records placeholders, risk flags, policy version, revision, and quarantine expiry.
4. LLM calls receive masked content only. `PrivacyGuard` fails closed if direct identifiers are detected.
5. Approval removes the quarantine object and starts the masked processing pipeline.
6. Builder/export replacement is limited to manifest-declared exact tokens.

The API currently has no authentication middleware or tenant isolation. `users` exists in the database model, but the active API flow still operates as a local single-user development experience. This must be resolved before treating the platform as a multi-tenant SaaS.

## 6. Current Versus Target Architecture

| Area | Current repository | Target direction |
|---|---|---|
| Frontend | React + Vite SPA | Keep SPA unless SSR/SEO becomes a product requirement |
| Backend | FastAPI modular monolith | Preserve module boundaries; split services only after measured operational need |
| LLM | OpenAI-compatible and Anthropic providers through one gateway | Add provider policy, cost budgets, tracing, and durable prompt/version metadata |
| RAG | Placeholder packages and design vocabulary | Add embeddings, vector storage, hybrid retrieval, reranking, and evaluation as a feature-scoped pipeline |
| Memory | Redis/session and PostgreSQL/profile directories are scaffolded | Define explicit session/profile contracts before wiring long-term memory |
| Multimodal | Parser and image features exist; ASR/video paths are placeholders | Add modality-specific adapters behind the same application contracts |
| Sandbox | Package placeholders only | Add isolated execution service with a security review before enabling code execution |
| Observability | Logging and task state are present; full OpenTelemetry/LangSmith wiring is not the current baseline | Add trace correlation across API, worker, LLM, and storage operations |
| Identity | No active auth/authorization boundary | Add authentication, ownership checks, tenant isolation, and secret rotation |

## 7. Design Rules

- `design/` contains stable cross-feature architecture; feature behavior belongs under `specs/`.
- API modules do not own domain policy. They validate transport input and delegate to application/domain code.
- Domain-derived LLM payloads must pass through the privacy policy before leaving the process.
- Background work persists state transitions and exposes retryable failure states.
- Frontend pages must represent loading, empty, success, and failure states for user-facing data flows.
- New data model changes require an Alembic migration and an update to `design/database.md` when the stable relationship model changes.
- A capability is considered implemented only when code, tests, and its feature specification agree.

## 8. Reading Order

For a system-level change, read this document first, then the relevant application-specific document:

1. `design/backend-architecture.md` for API, workers, domain, and infrastructure changes.
2. `design/frontend-architecture.md` for routes, components, state, and UI/API integration changes.
3. `design/database.md` for persistence changes.
4. The relevant `specs/<SPEC-ID>-<slug>/` feature specification and issue acceptance files.
