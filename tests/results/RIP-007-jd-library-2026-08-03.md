---
specId: RIP-007
specVersion: 2026-08-03
status: blocked_browser_acceptance
---

# RIP-007 Result

## Passed automated gates

| Issue | Evidence |
|---|---|
| 039 | Isolated PostgreSQL upgrade -> downgrade -> upgrade reached `j0e1f2a3b4c5`; JD migration backfill and later plan FK/index were present. |
| 040 | `backend/tests/unit/test_jd_import_service.py` covers trimmed text bounds plus object-store/database compensation; `test_jd_processing.py` covers file validation and parser failure. |
| 041 | `backend/tests/unit/test_safe_web_fetcher.py` covers unsafe URL shapes, IPv4/IPv6 non-global addresses, redirects, MIME, body limit, and timeout mapping. |
| 042 | `test_jd_plan_api.py::test_jd_processing_state_machine_preserves_manual_fields_and_safe_failures` and stale/duplicate tests cover run ownership, duplicate state, manual provenance, and safe failure. |
| 043-044 | `test_jd_plan_api.py` covers list/detail/patch, legacy compatibility codes, broker failure, matching refresh, and referenced-delete protection. |

Commands recorded on 2026-08-03:

```text
UV_CACHE_DIR=/private/tmp/uv-cache uv run --project backend pytest backend/tests/unit backend/tests/integration -q
# 212 passed, 1 skipped, 5 SwigPyDeprecationWarning warnings

UV_CACHE_DIR=/private/tmp/uv-cache uv run mypy api/v1/jd.py api/v1/plans.py api/v1/resume.py api/v1/router.py application/jd_import_service.py application/plan_service.py application/plan_regeneration_service.py application/plan_task_service.py domain/jd domain/job_search_plan infrastructure/web infrastructure/planners infrastructure/db/models.py tasks/jd_tasks.py tasks/plan_tasks.py
# Success: no issues found in 24 source files

pnpm lint
pnpm build
# passed; Vite emitted a non-failing >500 kB chunk warning

git diff --check
# passed
```

## Manual migration verification

An isolated temporary PostgreSQL database was upgraded to head, downgraded to `h8c9d0e1f2a3`, then upgraded to head again. The final version was `j0e1f2a3b4c5`; the partial unique index `uq_active_plan_jd_resume` and the JD/resume foreign keys were verified before that temporary database was dropped.

## Browser blocker

Issues 045, 046, and 047 remain blocked on their required desktop/mobile browser acceptance: three import modes, polling, duplicate actions, second edit, retry/re-extract, and layout screenshots. The local in-app browser controller timed out/reset and exposes no usable browser-control tool in this session. Lint and production build passed, but they are not substitutes for the required interaction evidence.

## Residual deployment control

`SafeWebFetcher` validates DNS before `httpx` opens the connection. A DNS-rebinding host could change between those operations, so the SPEC-required production outbound-egress restriction (or a pinned-IP transport) remains necessary. This is a deployment hardening condition, not a reason to weaken the existing URL, redirect, MIME, size, or timeout checks.
