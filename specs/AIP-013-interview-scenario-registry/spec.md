# AIP-013 Interview Scenario Registry

> Derived from `spec-draft/interview-plan-scenarios-2026-08-05.md` and `design/job-target-interview-architecture.md`
> Generated: 2026-08-05 | Target branch: `main` | Base commit: `8c05329` (dirty worktree)

## 1. Meta

| Field | Value |
|---|---|
| Spec ID | AIP-013 |
| Title | Interview Scenario Registry |
| Epic | Job Target Interview Training Program |
| Status | Proposed |
| Owner Agent | Backend Agent |
| Depends On | AIP-001 |
| Prerequisites | current interview stage/difficulty schemas; Pydantic v2; APIResponse envelope; recorded AIP-001 browser baseline before rollout |

## 2. Goal

Provide one code-owned, versioned Interview Scenario registry that validates stage, coverage, timing, follow-up, skip, language, difficulty, and scoring policy for all later Interview Plans and Sessions.

## 3. Why This Exists

Current AIP-001 accepts only question count and copied JD text. Adding scenario conditionals independently in pages, prompts, workflow nodes, and report code would create inconsistent policy and brittle tests. A small registry interface gives every caller one stable scenario snapshot and keeps policy versioning out of transport and prompt code.

## 4. Out of Scope

- Scenario admin CRUD, database persistence, user-authored scenarios, or prompt editing.
- Generating an Interview Plan, questions, evaluations, Sessions, or reports.
- Voice/video, RAG, Qdrant, Sandbox, whiteboard, or code execution modes.
- Company-specific or externally fetched interview content.
- Changing legacy AIP-001 request/response behavior.

## 5. Deliverables

- Typed `InterviewScenario` and nested stage/budget/follow-up/skip/scoring value objects.
- Seven version-1 fixtures defined in the target architecture.
- Registry validation and small query interface.
- Read-only scenario API and synchronized frontend types/i18n labels.
- Fixture, serialization, compatibility, and startup validation tests.

### Proposed Issue Mapping

| Issue | Scope | PRD coverage | Depends On |
|---|---|---|---|
| #116 | Scenario contracts, fixtures, registry API and tests | Plan US-002; FR-5 through FR-10 | #038 release gate |

## 6. Domain

### 6.1 Registry Interface

```text
ScenarioRegistry.list_active() -> tuple[InterviewScenarioSummary,...]
ScenarioRegistry.get(key, version?) -> InterviewScenario
```

The module hides fixture storage and validation. Callers select by `key`; omitting version resolves the current active version, while persisted Plans/Sessions always store the exact resolved version.

### 6.2 Required Fixtures

Keys are `comprehensive`, `hr_screen`, `technical_first`, `project_deep_dive`, `system_design`, `behavioral`, and `manager_round`, all version `1`. Exact stage order and emphasis are defined in `design/job-target-interview-architecture.md` section 5.

Each fixture contains:

- bilingual name/description keys, not display prose;
- ordered stages with integer weights totaling 100;
- allowed coverage categories and required candidate-question stage where applicable;
- duration-to-main-question budget `15:3`, `30:5`, `45:7`, `60:9`;
- duration-to-total-follow-up budget `15:1`, `30:3`, `45:5`, `60:7`;
- max follow-up depth 2;
- skip allowance `1` for 15/30 and `2` for 45/60, optionally lowered per fixture;
- allowed difficulty `basic/standard/challenge` and language `zh-CN/en`;
- scoring dimension keys and prompt-policy version.

### 6.3 Validation

Registry construction fails if keys/versions duplicate, stage weights do not sum to 100, budgets are non-monotonic/out of range, an unknown coverage/scoring key appears, candidate-question bounds are outside 1-3, or a fixture exceeds the global follow-up/skip policy.

## 7. Application

Scenario queries are synchronous in-process reads with no I/O, cache, database, or provider dependency. The API receives already validated domain snapshots. Interview Plan creation later resolves a fixture once and persists its version/config snapshot; it does not call `current` during Session execution.

Errors are `SCENARIO_NOT_FOUND` (404), `SCENARIO_VERSION_NOT_FOUND` (404), and internal startup/test failure `SCENARIO_REGISTRY_INVALID`. Invalid registry data must fail tests/startup rather than degrade to a generic scenario.

## 8. Repository

Expected areas:

```text
backend/domain/interview_scenario/             [NEW]
  schemas.py
  registry.py
  fixtures.py
backend/api/v1/interview_scenarios.py          [NEW]
frontend/src/api/interview-scenarios.ts        [NEW]
frontend/src/types/interview-scenarios.ts      [NEW]
frontend/src/i18n/locales/en.ts                [MODIFY]
frontend/src/i18n/locales/zh.ts                [MODIFY]
backend/tests/unit/test_interview_scenarios.py [NEW]
```

No port/adapter seam is introduced because the first release has one in-process fixture implementation. Tests exercise the same public registry interface.

## 9. API

| Method | Path | Response |
|---|---|---|
| GET | `/api/v1/interview-scenarios` | active scenario summaries and allowed global options |
| GET | `/api/v1/interview-scenarios/{key}` | current or `?version=` exact public scenario detail |

Public detail exposes stage names/weights, expected coverage categories, duration choices, question/follow-up counts, skip allowance, difficulty, and language. It does not expose prompts, planned questions, expected signals, or scoring rubrics.

## 10. Database Impact

None. Scenario definitions are versioned code fixtures. Persisted Interview Plans store the exact key/version and approved snapshot under AIP-014.

## 11. Test Plan

- Validate all seven fixtures and exact stage order.
- Validate weights, question/follow-up budgets, skip limits, candidate-question bounds, language/difficulty values, and scoring keys.
- Reject duplicate keys/versions, non-100 weights, unknown keys, and invalid monotonic budgets.
- API-test list/detail/not-found/version-not-found and absence of private fields.
- Frontend type/i18n-test every returned key without hard-coded fallback prose.
- Compatibility-test current AIP-001 enums remain untouched.

PRD mapping: Interview Plan US-002 and FR-5 through FR-10; the registry also supplies constraints used by Plan US-003/004 and Runtime US-002/004/006.

## 12. Definition of Done

- [ ] Seven scenario version-1 fixtures satisfy every invariant and serialize through one registry interface.
- [ ] API exposes only public policy data and supports exact version lookup.
- [ ] No scenario policy is duplicated in route/page/prompt code.
- [ ] Invalid fixture configuration fails deterministically.
- [ ] No database, RAG, provider, or admin dependency is introduced.
- [ ] Unit, API, frontend type/i18n, lint, and type checks pass.
