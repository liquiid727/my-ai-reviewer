# RIP-009 Test Contract

- Redactor: bilingual entities, overlaps, repeated values, deterministic tokens, empty text, malformed Unicode, and manifest cleartext exclusion.
- Gate: automatic approval, review required, manual spans, stale revision, engine unavailable, expiry, cleanup after every failure.
- Pipeline: enum status values cross the Celery boundary canonically; active LLM states, provider/worker timeout, bounded retry exhaustion, stale-worker no-op, and explicit masked-only retry converge safely.
- Persistence: annotated originals absent from masked text, text blocks, facts, evidence, profiles, drafts, histories, and API payloads.
- LLM: gateway spy proves annotated originals never reach extraction, evaluation, Builder, interview, match, or plan prompts.
- Export: full/partial replacements, unknown token, control/HTML input, photo validation, no persistence, same preview/download bytes, print fallback.
- Migration: dry-run has no writes; execute is idempotent and removes source/photo/export/AI-history artifacts.
- Frontend: empty, loading, success, failure, expiry, partial hydration, close-to-clear, download, and print on desktop/mobile.
- Celery runtime: every task module uses the same child-process event loop; forked workers discard inherited pools; a real PostgreSQL integration test runs watchdog then resume work in sequence.
