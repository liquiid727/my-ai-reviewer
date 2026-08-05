# [RIP-008] Plan and task schema/domain contracts

## Description

Introduce the independent plan aggregate, tasks, constraints, revisions and relationships to ready JD/resume/match data.

## Acceptance Criteria
- [ ] Add `job_search_plans` and `job_search_plan_tasks` models with every SPEC field
- [ ] Add status/category/source/priority checks, task/weekly-hour limits and indexes
- [ ] Add RESTRICT FKs to JD/resume, SET NULL match FK and CASCADE tasks FK
- [ ] Add partial unique index preventing duplicate unfinished plans for one JD+resume
- [ ] Add plan/task enums and strict Pydantic contracts
- [ ] Alembic migration depends on actual RIP-007 head and supports downgrade
- [ ] Update design database/domain relationship documentation
- [ ] Migration tests, ruff and mypy pass

## Dependencies

- `tasks/issues/issue-044-rip007-jd-state-command-api.md`

## Type

backend / database

## Priority

high

## PRD Reference

`tasks/prd-job-search-plans.md` - US-001; FR-1~FR-3, FR-8, FR-9, FR-22, FR-23

## SPEC Reference

`specs/RIP-008-job-search-plans/spec.md` - RIP-008 Sections 3.1~3.5

