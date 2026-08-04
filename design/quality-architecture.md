# Engineering Quality Architecture

**Status:** Target governance baseline
**Source:** `reviews/project-architecture-quality-2026-08-04.md`
**Program:** AIP-009 through AIP-012
**Last Updated:** 2026-08-04

This document defines how architecture quality is governed across the modular monolith. It does not claim that every target below is already implemented. Active enforcement is recorded in `rules/quality-gates.md`; migration work is tracked by the AIP-009 through AIP-012 issue sets.

## 1. Quality Ownership

| Concern | Canonical owner | Evidence |
|---|---|---|
| Stable system shape and target boundaries | `design/` | design diff and linked Spec |
| Mandatory dependency and directory constraints | `rules/architecture-boundaries.md` | architecture check output |
| Mandatory merge/release gates | `rules/quality-gates.md` | CI run and QA result |
| Feature behavior | `specs/<SPEC-ID>/` | acceptance matrix |
| QA procedure and reusable knowledge | `.agents/qa-agent.skill.md`, `skills/qa-quality-governance/` | QA report |
| Executable local entry points | `Makefile`, `scripts/quality/` | command exit status |
| Hosted enforcement | `.github/workflows/` and branch protection | required check status |

Design explains why; rules say what must hold; scripts and tests prove it; QA records the decision. The same rule must not be independently redefined in Agent prompts.

## 2. Target Dependency Model

```text
HTTP route / serializer
        |
        v
Application use case / transaction boundary ----> application-owned port
        |                                               |
        v                                               v
Pure domain policy                              infrastructure adapter
                                                        |
                                             DB / MinIO / Redis / LLM

main/bootstrap composition root wires ports to adapters.
Celery task invokes the same application use case with task context.
```

| Module | Owns | Allowed dependencies | Forbidden dependencies |
|---|---|---|---|
| `backend/api/` | HTTP validation, serialization, status/header mapping | application contracts, API schemas | ORM models, storage SDKs, LLM providers, Celery orchestration |
| `backend/application/` | use cases, transaction and retry boundaries, ports | domain, typed ports | FastAPI response types, provider SDK details |
| `backend/domain/` | entities, value objects, policies, domain errors | standard library, Pydantic where used as a value contract | application, infrastructure, FastAPI, Celery, SQLAlchemy, storage/LLM SDKs |
| `backend/infrastructure/` | adapter implementations | application/domain contracts, external libraries | API routers or user-visible response policy |
| `backend/tasks/` | process boundary and retry metadata | application use cases, task context | duplicated business policy or direct user response mapping |
| `frontend/src/pages/` | route-level workflow composition | feature components/hooks, stores, typed API modules | duplicate fetch/error decoders and backend error objects |
| `frontend/src/api/` | transport and typed response boundary | shared client and public types | page state or visual components |

FastAPI dependency providers are composition adapters, not business services. Any temporary boundary exception must be file-specific, owned, dated, and linked to a removal issue.

## 3. Decoupling Patterns

Patterns are selected to remove a demonstrated dependency or duplication. They are not acceptance criteria by name.

| Problem | Preferred pattern | Project use |
|---|---|---|
| Use case depends on DB/storage/LLM implementation | Protocol port + adapter | application owns the interface; infrastructure implements it |
| Route coordinates multiple state changes | Application service / command handler | one typed method owns transaction and orchestration |
| Runtime implementation selection | Strategy + factory | retain parser and LLM provider factories |
| Provider SDK leaks into core code | Anti-corruption adapter | normalize provider errors/results at the gateway boundary |
| Large API surface hides multiple workflows | Facade over cohesive use cases | router calls a narrow facade; facade must not become a generic god service |
| Risky incremental extraction | Characterization test + branch by abstraction | preserve behavior, introduce port, switch caller, remove old path |
| Long-running status behavior | Explicit state machine | validate transitions, terminal states, retries, run/revision ownership |
| Stable structured construction | Builder only where construction varies | do not introduce builders for ordinary Pydantic models |

Generic repositories are not the default. Repositories should represent an aggregate/use-case contract; unused `BaseRepository` abstractions are removed or justified by at least two real consumers.

## 4. Module And Directory Shape

New backend work follows the existing top-level layers and groups files by bounded context within them:

```text
backend/
  api/v1/<resource>.py
  application/<context>/
    commands.py          # only when command count warrants it
    queries.py
    services.py
    ports.py
    dto.py
  domain/<context>/
    entities.py
    values.py
    policies.py
    errors.py
  infrastructure/
    db/models/<context>.py
    db/repositories/<context>.py
    <adapter-kind>/<context>.py
  bootstrap/             # composition only
```

The frontend keeps shared transport under `src/api/` and types under `src/types/`. A complex workflow may add `src/features/<feature>/components`, `hooks`, and `state`; route pages remain thin composition surfaces.

Directory rules:

- Do not add an empty capability directory to imply that a runtime feature exists.
- Generated output stays out of source directories and Git unless its governing rule explicitly requires the artifact.
- Database models may be split into modules, but Alembic must continue importing one complete metadata graph.
- Compatibility re-exports may be used during extraction and must have a removal issue.
- File size is a review signal, not a standalone failure. A changed Python file above 400 lines or TSX file above 700 lines requires a responsibility/decomposition note; moving code without reducing coupling does not satisfy it.

## 5. Quality Gate Architecture

```text
developer change
  -> make lint / type-check / arch-check / test-*
  -> make ci (deterministic local aggregate)
  -> GitHub Actions jobs with the same underlying scripts
  -> QA evidence record
  -> review decision
  -> branch protection / release decision
```

Gate code belongs in small scripts under `scripts/quality/`; the Makefile and CI workflow call those scripts instead of maintaining divergent shell pipelines. Gate output must preserve exit codes and distinguish `PASS`, `FAIL`, `BLOCKED`, and `NOT_RUN`.

Adoption uses three stages:

1. Baseline recovery: fix current lint/type/test behavior; measure coverage and skips.
2. Ratchet: reject new findings while dated legacy exceptions are removed.
3. Full blocking: zero static/architecture findings, required tests green, no unexplained skips, and critical-path coverage targets enforced.

## 6. Test Evidence Contract

Each feature maps acceptance criteria to unit, integration/API, browser, migration, and privacy evidence as applicable. CI logs alone are not the normalized record; QA results under `tests/results/` contain the spec/ref/run identity, exact command, exit status, summary, and artifact references.

Required scenario categories are success, empty/loading where UI applies, validation failure, dependency failure, retry, conflict/stale ownership, timeout/expiry, concurrency, and privacy. `NOT_RUN` remains visible. An environmental failure may be `BLOCKED`; an assertion or behavior failure is `FAIL`.

## 7. Error Architecture

The core error contract is transport-independent:

```text
DomainError / ApplicationError
  code              stable machine identifier
  public_message    safe default, localization key or neutral text
  retryable         machine-readable retry meaning
  safe_details      allow-listed structured details only
  __cause__         internal exception chain, never serialized

API error mapper
  error type/code -> HTTP status + APIResponse envelope + request_id
```

- Domain code does not import HTTP status codes.
- Unknown exceptions map to a stable internal error and a generic public message.
- Validation, not-found, conflict, expired, dependency unavailable, timeout, and privacy rejection have explicit mappings.
- Raw exception strings, SQL/SDK details, prompts, filenames derived from PII, and stack traces never enter a public response or persisted business error field.
- Internal logs retain the exception chain under the redaction rules.

## 8. Logging And Correlation

One central logging configuration supports readable local output and structured production/CI output. Events use stable names and structured fields:

| Field | Meaning |
|---|---|
| `timestamp`, `level`, `event` | event identity |
| `request_id`, `trace_id` | synchronous and distributed correlation |
| `job_id`, `task_id`, `run_id`, `revision` | async ownership and stale-write analysis |
| `resource_type`, `resource_id`, `operation` | affected business resource |
| `error_code`, `retryable` | normalized failure semantics |
| `duration_ms`, `attempt` | performance/retry evidence |
| `provider`, `model` | allow-listed LLM metadata without payloads or credentials |

Correlation is accepted from a validated request header or generated at ingress, returned in the response, propagated through Celery headers/task context, and bound to LLM gateway events. A redacting filter denies configured keys and direct-identifier patterns at the output boundary. Prompts, completions, masked-to-real replacement maps, API keys, resume text, and quarantine data are never logged.

## 9. Rollout And Compatibility

- AIP-009 establishes rules and QA capability without changing business behavior.
- AIP-010 makes gates reproducible and green before they become protected checks.
- AIP-011 migrates one bounded context at a time behind characterization tests; temporary re-exports keep imports stable.
- AIP-012 introduces the error/logging foundation, migrates primary flows, then removes raw-error paths.
- Branch protection activation is recorded separately because it changes external repository state.
- Any emergency waiver includes rule ID, exact scope, owner, reason, expiry date, and removal issue. Permanent broad allowlists are forbidden.
