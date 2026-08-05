# [AIP-017] Build complete/incomplete report worker and lifecycle

Generate constrained report prose/recommendations asynchronously without recomputing scores or changing terminated status.

## Acceptance Criteria

- [ ] Dispatch normal complete and eligible terminated-incomplete reports with separate report run/status.
- [ ] Build bounded relational aggregate and call report writer outside transaction.
- [ ] Reject unknown evidence/recommendation keys, dimension disagreement, malformed output, and privacy leakage.
- [ ] Finalize one immutable report only under current run/status; normal completing Session becomes completed, terminated remains terminated.
- [ ] Persist safe failure/retryability, support explicit retry without re-evaluation, and block stale overwrite.
- [ ] Worker/integration tests cover broker failure, timeout, retry, duplicate task, stale run, and zero-answer behavior.

- **Type:** backend
- **Priority:** high
- **Depends on:** #135
- **SPEC:** AIP-017 sections 7.1/7.3, 8
