# Engineering Quality Governance Draft

**Source review:** `reviews/project-architecture-quality-2026-08-04.md`
**Requested at:** 2026-08-04
**Status:** Accepted for technical specification
**Operating mode:** GoalSpec

## Intent

Turn the 2026-08-04 project architecture review into an enforceable quality-management program. The program must improve architecture boundaries, test and CI gates, module decomposition, error handling, logging, directory ownership, and the QA Agent's reusable knowledge without interrupting unrelated feature delivery.

## Baseline

- Architecture quality score: 2.4/5.
- Backend checks at review time: 14 Ruff findings, 45 mypy errors, 231 passed and 4 failed pytest cases.
- Frontend lint/build passed, but there is no automated frontend test command and the main bundle is about 1 MB.
- Domain modules import application/infrastructure code, and several API routers orchestrate ORM, storage, LLM, or Celery details directly.
- Error responses mix business codes, `HTTPException`, and raw exceptions.
- Logging has no central configuration, cross-process correlation contract, or enforceable PII redaction.
- Current-state, roadmap, design, and older Agent instructions contain conflicting technology and delivery-mode descriptions.

The numbers above describe one reviewed working tree. They are evidence for prioritization, not a permanent allowlist or a future passing threshold.

## Required Outcomes

1. A single quality architecture and a small set of normative architecture/quality rules become the source of truth.
2. The QA Agent loads task-specific quality knowledge, executes reproducible gates, emits standardized evidence, and never converts `NOT RUN` or `BLOCKED` into `PASS`.
3. Local and CI entry points expose equivalent lint, type, architecture, unit, integration, frontend, build, and full-CI checks.
4. Existing failures are removed before full blocking gates are enabled; temporary ratchets must expire and cannot hide new findings.
5. API/Application/Domain/Infrastructure dependencies are migrated incrementally behind use cases and ports.
6. Large Resume, Builder, JD/Plan, ORM, and frontend modules are split by responsibility with characterization tests protecting behavior.
7. Stable error codes and safe public messages are separated from internal causes and HTTP mapping.
8. Structured logs correlate API, Celery, LLM, and resource work without logging prompts, resumes, secrets, or direct identifiers.
9. Directory and ownership rules distinguish active runtime capabilities from placeholders and generated evidence.

## Program Slices

| Spec | Scope | Depends On |
|---|---|---|
| AIP-009 | Quality governance, rules, QA knowledge, evidence format | none |
| AIP-010 | Baseline recovery, Make targets, tests, CI gates | AIP-009 |
| AIP-011 | Executable dependency rules and modular decomposition | AIP-009, AIP-010 |
| AIP-012 | Error taxonomy, structured logging, correlation, redaction | AIP-009, AIP-010 |

## Success Measures

- Ruff, mypy, unit tests, required integration tests, frontend tests/lint/build, and architecture checks are green on protected changes.
- New architecture violations cannot be added without a dated, owned exception.
- All public failures use a stable code and safe message; unknown failures do not expose internal exception text.
- API-to-worker-to-LLM flows can be followed with correlation fields in synthetic-data tests.
- Changed large modules show a measurable responsibility reduction, not line-count movement alone.
- QA results are reproducible from recorded commands, refs, environment, and evidence paths.

## Non-Goals

- A one-shot rewrite into microservices or strict Clean Architecture.
- Adding authentication, multi-tenancy, production SIEM, or a new observability vendor.
- Enforcing arbitrary design patterns or deleting extension-point directories without checking active imports/specs.
- Changing business behavior while extracting module boundaries.
- Enabling merge/push/branch-protection changes without explicit delivery authorization.

## Assumptions

- Python 3.12 is the development and CI target; project metadata compatibility must be made consistent in AIP-010.
- PostgreSQL remains the business state source; Redis and MinIO keep their current roles.
- GitHub Actions is the intended hosted CI system because the repository uses GitHub issue/ship workflows, but branch protection is an external configuration step.
- Coverage thresholds will be based on a measured baseline and critical-path targets, not an invented repository-wide number.
