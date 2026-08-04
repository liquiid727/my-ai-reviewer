# AIP-012 Error And Observability Foundation

> Derived from `spec-draft/engineering-quality-governance-2026-08-04.md` and AIP-009
> Generated: 2026-08-04 | Target branch: `main` | Base commit: `89c87f6`

## 1. Meta

| Field | Value |
|---|---|
| Spec ID | AIP-012 |
| Title | Error And Observability Foundation |
| Epic | Engineering Quality Governance |
| Status | Proposed |
| Owner Agent | Backend Agent |
| Depends On | AIP-009, AIP-010 |
| Prerequisites | shared APIResponse envelope, privacy guard, green error/logging test baseline |

## 2. Goal

Provide stable transport-independent errors, uniform API mapping, safe frontend semantics, structured logs, and correlation across API, Celery, LLM, and resource state without exposing sensitive data.

## 3. Why This Exists

The current code mixes business codes, `HTTPException`, `ValueError`, and broad exception handling. Global handlers cover only a few errors, stored/raw exception text can reach status APIs, and logs lack one configuration or request/task/trace contract. Silent compensation and uncorrelated async work make failures hard to diagnose.

## 4. Out of Scope

- Selecting a production telemetry vendor or deploying a SIEM.
- Adding authentication, tenant audit logs, or a public trace-search API.
- Logging prompts, completions, resume/JD text, replacement maps, credentials, or direct identifiers.
- Changing business retry/state rules except to make existing semantics explicit and consistent.

## 5. Deliverables

- Domain/application error base types with stable code, safe message, retryable flag, safe details, and chained internal cause.
- Central API error mapper and unknown/validation handlers returning the existing envelope and request ID.
- Migration of Resume, JD/Plan, and Builder primary flows away from raw public/persisted exception text.
- Central structured logging configuration, context binding, event naming, and redaction filter.
- Request/trace/job/task/run/revision/resource correlation through API, Celery, and LLM gateway.
- Synthetic canary tests for response/log/task/LLM privacy and retry semantics.

## 6. Domain

Errors are transport-independent and categorized at least as validation, not found, invalid state, conflict, expired, privacy rejected, dependency unavailable, timeout, and internal. HTTP status mapping is API-owned. Retryability is explicit; conflict/stale ownership means reconcile/reload, not blind retry.

## 7. Application

Use cases translate adapter/provider failures into stable application errors using exception chaining. The API mapper serializes allow-listed details and a request ID. Unknown failures log once at the owning boundary and return a generic message. Persisted failure fields store a safe code/message/diagnostic reference, never a raw cause.

Logging binds context at ingress and process boundaries. Celery headers/task context carry correlation and ownership values; LLM gateway events record provider/model/duration/token metadata but not inputs/outputs. The redaction filter is the final log-output guard.

## 8. Repository

Expected implementation areas:

- domain/application error modules and API mapper/handlers;
- `backend/observability/` logging, context, events, and redaction;
- `backend/main.py` middleware/handler registration;
- target application services, tasks, and `infrastructure/llm/gateway.py`;
- frontend shared error mapping/i18n where public semantics change;
- unit/integration tests with synthetic canaries and log capture.

## 9. API

Existing endpoints retain their paths and success schemas. Error responses use the shared envelope with stable code, safe message, optional allow-listed data, and `request_id` in the envelope or response header. Validation, not-found, conflict, expired, dependency failure, timeout, privacy rejection, and unknown errors have explicit HTTP mappings. Binary endpoints return safe headers/error bodies without echoing multipart values.

## 10. Database Impact

No schema change is required for the foundation. If implementation discovers that safe persisted diagnostics cannot fit existing fields without semantic overload, that change requires a separate migration Spec and `design/database.md` update.

## 11. Test Plan

- Unit-test error construction, chaining, safe-detail allowlist, retryability, and HTTP mapping.
- API-test success plus validation/not-found/conflict/expired/dependency/timeout/privacy/unknown branches.
- Assert raw exception canaries never appear in responses or persisted error/status fields.
- Capture structured logs and assert event/correlation/resource fields plus redaction.
- Exercise synthetic API -> Celery -> LLM flow and verify correlation propagation and stale run/revision behavior.
- Verify frontend maps stable codes to translated recovery states and never renders raw backend objects.

## 12. Definition of Done

- [ ] Primary API flows use stable error types and one global mapping contract.
- [ ] No raw exception text or sensitive payload is user-visible, persisted as public failure state, or emitted to logs.
- [ ] Unknown errors return a generic safe response and a correlatable request ID.
- [ ] API, Celery, LLM, and resource events share correlation/ownership fields.
- [ ] Retry, conflict, expiry, stale-worker, and privacy behavior is tested and consistent.
- [ ] QA can reproduce a failure chain using synthetic evidence without a production telemetry service.
