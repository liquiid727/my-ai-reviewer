# RIP-008 Tasks

**Feature**: AI 求职计划列表
**Status**: Implementation detected; acceptance reconciliation pending (#092)
**PRD**: `tasks/prd-job-search-plans.md`
**SPEC**: `specs/RIP-008-job-search-plans/spec.md`
**Depends on**: RIP-007 issue-044 for backend contracts; issue-046 for plan-entry UI

## Issue List

> 2026-08-05 drift note: plan domain/API/worker/frontend code exists, but the checkboxes remain unchanged until issue #092 verifies each contract. RIP-012 issue #104 will replace timestamp-only match freshness with the versioned fingerprint contract.

- [ ] [issue-048: Plan and task schema/domain contracts](../../tasks/issues/issue-048-rip008-plan-task-schema.md)
- [ ] [issue-049: Eligible resume options, match freshness and Source Catalog](../../tasks/issues/issue-049-rip008-plan-source-catalog.md)
- [ ] [issue-050: Structured LLM plan generator](../../tasks/issues/issue-050-rip008-llm-plan-generator.md)
- [ ] [issue-051: Plan create, list, detail and retry pipeline](../../tasks/issues/issue-051-rip008-plan-generation-api.md)
- [ ] [issue-052: Task CRUD, revision control and plan progress](../../tasks/issues/issue-052-rip008-plan-task-crud.md)
- [ ] [issue-053: Atomic plan regeneration and protected deletion](../../tasks/issues/issue-053-rip008-plan-regeneration.md)
- [ ] [issue-054: Plan navigation, list and creation UI](../../tasks/issues/issue-054-rip008-plan-list-create-ui.md)
- [ ] [issue-055: Plan detail task editor and autosave](../../tasks/issues/issue-055-rip008-plan-detail-editor-ui.md)
- [ ] [issue-056: Plan generation recovery and regeneration UI](../../tasks/issues/issue-056-rip008-plan-regeneration-ui.md)
- [ ] [issue-057: Plan integration, browser acceptance and traceability closeout](../../tasks/issues/issue-057-rip008-plan-acceptance.md)

## Dependency Order

```text
044 → 048 → 049 → 050 → 051
          └────────→ 052
050 + 052 → 053
046 + 051 → 054
052 + 054 → 055
053 + 055 → 056
047 + 056 → 057
```

Post-MVP `TODO-PLAN-001` ~ `TODO-PLAN-008` remain in the PRD and are not part of this task set.
