# AIP-011 Architecture Modularization

> Derived from `spec-draft/engineering-quality-governance-2026-08-04.md` and AIP-009
> Generated: 2026-08-04 | Target branch: `main` | Base commit: `89c87f6`

## 1. Meta

| Field | Value |
|---|---|
| Spec ID | AIP-011 |
| Title | Architecture Modularization |
| Epic | Engineering Quality Governance |
| Status | Proposed |
| Owner Agent | Architecture Agent |
| Depends On | AIP-009, AIP-010 |
| Prerequisites | green characterization baseline, architecture rules, executable gate interface |

## 2. Goal

Incrementally enforce API -> Application -> Domain/Ports -> Infrastructure ownership and split the highest-risk Resume, JD/Plan, Builder, ORM, and frontend modules without changing public behavior.

## 3. Why This Exists

Domain services currently import application and infrastructure code, and API routes directly operate ORM, MinIO, LLM, or task details. Several 500-1800 line modules combine transport, persistence, privacy, rendering, LLM, and UI state. These dependencies make isolated tests and safe feature changes expensive.

## 4. Out of Scope

- Microservices, a dependency-injection framework, or a repository-wide rewrite.
- Generic repositories/facades/base classes without demonstrated consumers.
- API, database, privacy, or workflow behavior changes hidden inside refactoring.
- Deleting planned extension points unrelated to changed runtime documentation.

## 5. Deliverables

- Executable dependency checker with expiring, file-specific exceptions.
- Application-owned typed use cases and ports for Resume, JD/Plan, and Builder side effects.
- Infrastructure adapters wired at a composition root; thin routes and Celery tasks.
- ORM model modules split by aggregate while preserving metadata and migrations.
- Builder backend and frontend decomposed by workflow/responsibility.
- Shared frontend transport/error/polling behavior with feature-specific binary/multipart contracts isolated.

## 6. Domain

Domain modules contain pure entities, values, policies, state transitions, and transport-independent errors. They do not own sessions, SDK clients, object paths, LLM selection, or HTTP responses. State/revision/run ownership remains a domain/application invariant through extraction.

## 7. Application

Each use case accepts a typed command/query and ports, owns its transaction/status transition, and returns a typed result/error. Characterization tests are added before switching a caller. Construction occurs in `backend/bootstrap/` or an approved composition provider. Compatibility re-exports are temporary and issue-linked.

## 8. Repository

- `backend/application/<context>/` owns use cases, DTOs, and ports.
- `backend/domain/<context>/` retains pure policy and value contracts.
- `backend/infrastructure/` implements DB/storage/parser/LLM/rendering adapters.
- `backend/infrastructure/db/models/` becomes aggregate modules with one metadata graph.
- `frontend/src/features/builder/` owns complex Builder components/hooks while `src/api/` and `src/types/` remain canonical transport/type boundaries.
- `scripts/quality/architecture_check.*` and a narrow exception registry enforce imports.

## 9. API

No endpoint path, request/response schema, status code, or binary contract changes are intended. Contract tests compare behavior before and after each extraction.

## 10. Database Impact

No schema change. ORM file splitting must not generate an Alembic diff, change table names/columns/constraints, or omit models from metadata.

## 11. Test Plan

- Characterization tests for success, failure, retry, conflict, expiry, privacy, and stale run/revision behavior before each slice.
- Architecture tests for forbidden imports, dynamic/local imports, exception expiry, and new-file coverage.
- API contract snapshots/assertions before and after route thinning.
- Alembic metadata/migration smoke after model splitting.
- Frontend component/browser checks for Builder empty/loading/success/failure/pending/conflict/export flows.
- Compare dependency edges, constructor inputs, duplicate decoders/pollers, and module responsibilities before/after.

## 12. Definition of Done

- [ ] No domain imports application/infrastructure/framework/SDK code.
- [ ] Target API routes do not orchestrate ORM, MinIO, LLM provider, or Celery details.
- [ ] Architecture gate is zero-error or contains only valid expiring exceptions with removal issues.
- [ ] Public API, DB schema, privacy, retry, and concurrency behavior remains compatible.
- [ ] Builder/Resume/ORM hotspots have narrower named responsibilities and independently testable units.
- [ ] Frontend transport, error decoding, and polling have one canonical implementation per contract.
