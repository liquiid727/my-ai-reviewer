# AIP-012 Test Contract

| Scenario | Required assertions |
|---|---|
| validation/not-found/state/conflict/expired | stable code, HTTP mapping, safe message, request ID |
| provider/storage/database timeout | retryable semantics, chained cause, no SDK/raw text response |
| unknown exception | generic 500 response, one redacted stack event, correlation present |
| persisted failure/status | safe code/message only; raw canary absent |
| API -> task -> LLM | request/trace/job/task/run/resource context preserved |
| stale task/revision | no newer state overwrite; log names owner mismatch safely |
| privacy/log redaction | secrets, identifiers, prompts, completions, resume and replacements absent |
| frontend recovery | translated retry/reload/conflict/expired state; no raw object display |
