# Architecture Boundary Rules

**Rule set:** ARCH-1
**Applies to:** new and modified production code
**Design source:** `design/quality-architecture.md`

The keywords MUST, MUST NOT, SHOULD, and MAY are normative.

## Dependency Rules

- `ARCH-001`: `backend/domain/` MUST NOT import `backend.application`, `backend.infrastructure`, FastAPI, Celery, SQLAlchemy, MinIO, Redis, or provider SDKs.
- `ARCH-002`: route modules under `backend/api/` MUST delegate business orchestration to application use cases and MUST NOT import ORM models, storage/LLM adapters, or Celery task implementations.
- `ARCH-003`: application ports MUST be owned by application/domain code; infrastructure adapters MAY implement them. Core modules MUST NOT import an adapter to construct it.
- `ARCH-004`: provider-specific requests, responses, exceptions, credentials, and retry quirks MUST end at infrastructure adapters.
- `ARCH-005`: Celery tasks MUST be thin boundaries with explicit retry, terminal-state, run/revision, and stale-worker behavior.
- `ARCH-006`: async API/application code MUST NOT execute unisolated blocking I/O.
- `ARCH-007`: frontend pages MUST use typed modules under `frontend/src/api/` and MUST NOT add a second generic response/error decoder.
- `ARCH-008`: binary and multipart feature contracts MAY use feature-specific clients, but MUST share authentication, correlation, safe error decoding, and cancellation behavior where applicable.

## Composition Rules

- `ARCH-009`: Object construction and adapter binding MUST occur in an explicit composition location such as `backend/bootstrap/`, app startup, or a narrowly scoped dependency provider.
- `ARCH-010`: A dependency-provider exception MUST NOT contain business policy.
- `ARCH-011`: Domain and application tests SHOULD construct ports with in-memory fakes instead of patching provider SDKs.

## Directory Rules

- `ARCH-012`: Active runtime packages MUST correspond to an implemented Spec and executable wiring. Placeholder packages MUST be labeled as planned and MUST NOT be described as active services.
- `ARCH-013`: New top-level backend or frontend directories require a `design/` update explaining ownership and dependency direction.
- `ARCH-014`: Database models split across files MUST remain registered in Alembic metadata and MUST preserve migration determinism.
- `ARCH-015`: Generated files, coverage output, build artifacts, caches, uploads, and secrets MUST NOT be committed to source directories.
- `ARCH-016`: Compatibility shims and re-exports MUST name a removal issue and MUST NOT become a second canonical implementation.

## Decomposition Rules

- `ARCH-017`: Refactoring MUST begin with behavior/characterization tests for the affected public contract.
- `ARCH-018`: A split MUST reduce at least one measured concern: dependency edges, responsibilities, duplicated protocol handling, mutation ownership, or test setup cost.
- `ARCH-019`: Moving lines into helper files without changing ownership or dependency direction does not count as decomposition.
- `ARCH-020`: A changed Python file over 400 lines or TSX file over 700 lines MUST include a QA/review note that identifies responsibilities and either links a split issue or justifies cohesion.
- `ARCH-021`: Design patterns MUST solve a stated problem. New factories, repositories, facades, or base classes require concrete consumers and tests.

## Enforcement And Exceptions

`make arch-check` is the target executable gate defined by AIP-010/AIP-011. Before it is active, QA runs the direct import scan and manual contract review described by `.agents/qa-agent.skill.md`.

- `ARCH-022`: An exception record MUST include rule ID and exact file/import; reason the boundary cannot yet be removed; owner and linked issue; creation and expiry dates; and proof that no new call sites are covered by the exception.
- `ARCH-023`: Expired, wildcard, directory-wide, or ownerless exceptions fail the architecture gate.
