# [AIP-012] Propagate Celery and LLM correlation context

Carry request/trace/job/task/run/revision/resource ownership from API dispatch through workers and LLM gateway events.

## Acceptance Criteria
- [ ] Celery dispatch/task context preserves validated correlation and resource ownership fields
- [ ] LLM gateway logs provider/model/duration/token/error metadata without request/response content
- [ ] Retries retain correlation, increment attempt, and do not allow stale run/revision writes
- [ ] Synthetic API-to-task-to-LLM tests prove propagation and redaction

- **Type:** backend
- **Priority:** high
- **Depends on:** #089
- **SPEC:** `specs/AIP-012-error-observability/spec.md` (Sections 7-8, 11)
