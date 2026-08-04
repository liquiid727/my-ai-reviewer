---
standardVersion: specos-test-standard/v1
qualityProfile: fullstack-security-migration
riskTier: P1
specId: RIP-007
specVersion: 2026-08-03
featureName: JD library and intelligent extraction
source:
  - tasks/prd-jd-library.md
  - specs/RIP-007-jd-library/spec.md
  - specs/RIP-007-jd-library/tasks.md
flakePolicy: Retry only transport-dependent browser checks; do not retry API, migration, or security assertions.
dataPolicy: Use isolated PostgreSQL schema/database data and synthetic resume/JD fixtures only.
securityPolicy: No outbound test requests; URL fetch tests use httpx MockTransport and assert SSRF rejection before a request is sent.
---

# RIP-007 Test Plan

## Flows

| Flow | Ordered stages | Scenarios |
|---|---|---|
| Import and extraction | validate -> persist -> dispatch -> source extract -> duplicate check -> LLM merge | text/file/url, invalid input, dispatch failure, stale run, duplicate decision |
| Library operations | list -> detail -> patch -> recovery/delete | filters, optimistic conflict, manual provenance, retry, re-extract, referenced delete |
| Downstream reuse | ready JD -> match / plan entry | legacy matching regression and JD plan preselection |

## Endpoint Coverage

| Interface | Branches and expected result | Evidence |
|---|---|---|
| `POST /jd/import/text` | trimmed 1..100000 input; verified-config gate; durable processing record | `test_jd_import_service.py` |
| `POST /jd/import/file` | extension/MIME/10MB validation; `jd/` storage ownership; rollback/compensation | `test_jd_import_service.py`, `test_jd_processing.py` |
| `POST /jd/import/url` | HTTP(S) only; credentials/ports/non-global DNS/redirect/MIME/body/timeout rejection | `test_safe_web_fetcher.py` |
| `GET/PATCH /jd` | projected list, filter/sort, detail, manual field provenance, 1003 conflict | `test_jd_plan_api.py` |
| `POST /jd/{id}/retry`, `/reextract`, duplicate commands | state/run protection and safe recovery | `test_jd_plan_api.py` state-machine/stale-run/broker-failure cases; browser scenario pending |
| `DELETE /jd/{id}` and `POST /jd/match` | plan reference returns 1005; legacy synchronous create and ready-only match stay compatible | `test_jd_plan_api.py` |

## Traceability

| PRD scope | Requirements | Issues | Automated evidence | Visual/browser evidence |
|---|---|---|---|---|
| US-001 persistent lifecycle | FR-1, FR-7, FR-8 | 039, 042 | Alembic round-trip; `test_jd_processing.py`; `test_jd_plan_api.py` state machine | pending local-browser controller |
| US-002 three import sources | FR-2..FR-6, FR-9..FR-12 | 040, 041, 042 | `test_jd_import_service.py`, `test_safe_web_fetcher.py`, `test_jd_processing.py` | pending three-mode import scenario |
| US-003 list/filtering | FR-15 | 043, 045 | `test_jd_plan_api.py` | pending desktop/mobile list scenario |
| US-004 import UI/duplicate | FR-16, FR-17 | 042, 045 | backend duplicate state tests | pending confirmation/cancel scenario |
| US-005 structured correction | FR-13, FR-14 | 043, 046 | `test_jd_plan_api.py` conflict/provenance assertions | pending second-edit/persistence scenario |
| US-006 recovery/deletion | FR-1, FR-20 | 044, 047 | `test_jd_plan_api.py` referenced-delete assertion | pending retry/re-extract/delete dialog scenario |
| US-007 downstream reuse | FR-18, FR-19 | 046, 047 | legacy match regression; plan integration assertion | pending JD deep-link scenario |

## Production Gates

| Requirement ID | Layer | Applies to | Required evidence | Gate impact |
|---|---|---|---|---|
| RIP7-MIGRATION | migration | 039, 047 | upgrade -> downgrade -> upgrade on isolated PostgreSQL database | blocking |
| RIP7-SECURITY | unit/security | 041, 047 | IPv4/IPv6/redirect/MIME/body-limit/timeout assertions | blocking |
| RIP7-API | unit/integration | 040, 042..044, 047 | service/API regression suite, ruff, mypy | blocking |
| RIP7-UI | lint/build/browser | 045..047 | lint/build plus desktop/mobile interaction screenshots | blocking until browser evidence exists |
