# Feature Spec Example

## Meta

- Spec ID: `RP-002`
- Title: `RP-002 Decision API`
- Epic: `Risk Platform / Foundation`
- Status: `draft`
- Owner Agent: `implementation-agent`
- Depends On:
  - `RP-003`
  - `RP-004`
- Prerequisites:
  - Identity Platform already provides `principal_no`, `user_no`, and `tenant_no`
  - Registry already provides `app_no`

## Goal

Describe the business goal this feature slice must deliver.

## Why This Exists

Explain why the feature exists, what business gap it closes, and why it must be a standalone slice.

## Out of Scope

- Rule engine internals
- Policy CRUD
- Profile CRUD
- Admin UI

## Deliverables

- migration
- entity
- repository
- application service
- HTTP handler
- DTO
- OpenAPI update
- unit test
- integration test
- audit event

## Domain

- Core entities and value objects
- Domain rules and invariants
- State transitions

## Application

- Use case orchestration
- Validation flow
- External dependency calls

## Repository

- Persistence model
- Read/write paths
- Cache or index usage

## API

- `POST /api/risk/decision`
- Request/response summary
- Error semantics

## Database Impact

- New table `risk_decision_log`
- New index on `tenant_no, principal_no`

## Test Plan

- Happy path
- Boundary conditions
- Error cases
- Audit and observability checks
- Benchmark or latency check when required

## Definition of Done

- [ ] API is callable
- [ ] Migration is complete
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] OpenAPI is updated
- [ ] Audit event is emitted
- [ ] Documentation is updated
- [ ] Benchmark or performance evidence is recorded when required
