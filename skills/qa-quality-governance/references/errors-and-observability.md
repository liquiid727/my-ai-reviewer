# Errors And Observability Knowledge

## Error Review

Trace every failure across four representations:

| Boundary | Expected content |
|---|---|
| Domain/application | stable code/category, safe message, retryable meaning, safe details, chained internal cause |
| API | HTTP status, `APIResponse` envelope, stable code, public message, request ID |
| Frontend | translated actionable state, retry/reload/conflict behavior, no backend object dump |
| Internal log | error code, correlation/resource fields, stack trace where useful, redacted cause |

HTTP semantics belong at the transport mapping boundary. Unknown errors use a generic public response while preserving a redacted internal exception chain. Never serialize `str(exc)` by default.

Check persisted failure fields as carefully as immediate responses: status polling often exposes stored `parse_error` or task/provider text later.

## Retry Semantics

`retryable` is a contract, not a guess by the UI. Validation, privacy rejection, and state conflicts are normally non-retryable without user change; dependency unavailable and timeout may be retryable; stale revision/run ownership requires reload/reconciliation rather than blind retry.

Celery retry policy must agree with the application error category and preserve the latest run/revision owner.

## Logging Review

Each event should answer what operation happened, to which synthetic resource ID, under which request/task/run, with what outcome and duration. Message strings alone are insufficient for cross-process analysis.

Reject:

- raw resume/JD contents, prompts, completions, replacement maps, file bytes, credentials, tokens, cookies, or precise identifiers;
- string interpolation of request bodies or exception objects with unknown payloads;
- silent compensation without a warning/error event;
- duplicate stack traces at every layer;
- provider-specific fields outside the adapter/gateway boundary.

Allow only deliberate metadata such as provider/model name, token counts, latency, stable error code, attempt number, and opaque resource IDs.

## Correlation Path

Validate one synthetic request through:

```text
HTTP ingress -> application use case -> Celery dispatch -> worker -> LLM gateway -> terminal state
```

The request ID is validated/generated at ingress and returned to the client. Trace/job/task/run/resource identifiers are added as the workflow crosses boundaries. Tests should prove propagation and redaction without requiring a production telemetry backend.

## Privacy Evidence

Use synthetic canary values in tests. Assert that canaries are absent from captured logs, API errors, task metadata, result artifacts, and LLM spy payloads. Redaction failure must fail closed at privacy-sensitive egress.
