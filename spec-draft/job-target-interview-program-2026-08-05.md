# Job Target Interview Program Intake

**Status**: Approved for specification

**Prepared**: 2026-08-05

**Operating mode**: GoalSpec

**Product direction source**: `spec-draft/career-agent-product-direction-2026-08-04.md`

**Workflow source**: `spec-draft/career-agent-workflow-2026-08-05.md`

## 1. Purpose

This intake turns the 2026-08-04 product positioning and the 2026-08-05 workflow proposal into four reviewable PRDs. It defines the shared product language, current implementation baseline, cross-domain invariants, delivery order, and scope limits that those PRDs must follow.

This document is not a formal feature SPEC and does not authorize implementation. Its approval authorizes design, proposed feature Specs, and Issue decomposition; implementation still requires an approved Issue and the delivery gates in section 8.

## 2. Product Positioning

The product is a **JD-driven job-search and interview-training agent for technical candidates**.

Its core value is not merely writing a resume or running a chat interview. For one target role, it must connect evidence-backed candidate facts, a specific JD version, a reproducible match assessment, an approved interview strategy, a recoverable interview session, and an actionable report.

The target user journey is:

```text
Import or create a JD
  -> review and publish an immutable JD version
  -> choose an immutable resume version
  -> create or reuse a Job Target
  -> run an evidence-backed match assessment
  -> generate and approve an Interview Plan
  -> start and complete an Interview Session
  -> review the report and explicitly add follow-up work to a job-search plan
```

## 3. Current Baseline And Delta

The new PRDs extend existing modules. They must not describe existing capability as greenfield work.

| Area | Current as-built baseline | Required program delta |
|---|---|---|
| JD library | RIP-007 supports text, file, and public URL import; editable structured fields; duplicate detection; retry/re-extract; list/detail UI | Add image OCR and manual creation, richer evidence-backed schema, review/publish lifecycle, and immutable versions |
| Matching | RIP-003 persists a deterministic required-skill match against a Candidate Profile | Pin inputs to immutable versions; add multidimensional scoring, policy versioning, evidence classes, caps, and a complete report workflow |
| Job-search plans | RIP-008 persists editable AI/manual tasks with evidence, revisions, retry, and regeneration | Reuse as the destination for explicitly accepted interview follow-up tasks; do not create a competing learning-task store in this program |
| Interview creation | AIP-001 creates an interview directly from a resume or Builder draft plus copied `jd_text` | Insert an Interview Plan resource between input selection and session start; reference version IDs instead of copied mutable inputs |
| Interview runtime | AIP-001 supports text questions, evaluation, follow-up, persistence, and asynchronous reporting | Add scenario-driven orchestration, pause/resume/skip/terminate, coverage control, event history, idempotency, and delayed feedback |
| Privacy | RIP-009 provides masked resume processing and a fail-closed PrivacyGuard | Every resume version and LLM-facing interview input must remain masked; no raw identifiers in prompts, logs, snapshots, tests, or screenshots |

Known documentation drift must be handled during the later SPEC stage: some historical task lists still report JD, plans, or AIP-001 as unimplemented even though the code and test evidence exist. New PRDs cite the as-built baseline and do not use those stale statuses as implementation truth.

## 4. Shared Domain Language

| Term | Meaning |
|---|---|
| Job Description | Stable identity for one imported or manually created role description and its source history |
| JD Version | Immutable published snapshot of normalized JD content, structured requirements, evidence, parser/schema versions, and confirmation metadata |
| Resume Version | Immutable masked snapshot derived from a parsed resume or a specific Builder draft revision, including the candidate/profile data allowed for matching and interview use |
| Job Target | Minimal workspace that groups one target JD with selected resume versions, match assessments, interview plans, sessions, and job-search plans |
| Match Assessment | Immutable result for exactly one JD Version, one Resume Version, and one scoring-policy version |
| Interview Scenario | Versioned template defining stages, competencies, interviewer behavior, timing defaults, follow-up policy, and scoring dimensions |
| Interview Plan | Generated, reviewable strategy for one Job Target and exact input versions; approval is required before a session can start |
| Interview Session | One execution of one approved Interview Plan; runtime state is independent of plan-generation state |
| Coverage Item | One competency or risk that the session should assess, with source, importance, question coverage, score, and evidence sufficiency |
| Answer Evaluation | Internal structured assessment of one answer used for follow-up and final reporting; hidden from the user until the session ends |

## 5. Cross-Domain Invariants

1. A JD or resume edit never changes the meaning of an existing match, plan, session, or report.
2. Published JD Versions and Resume Versions are immutable. A correction creates a new version.
3. A Job Target is created idempotently on the first downstream action, not when a JD is merely saved to the library.
4. The same anonymous user scope has at most one active Job Target for a JD identity; archived targets remain historical.
5. A Match Assessment always records its exact input version IDs and scoring-policy version.
6. Match recommendations are advisory. A low score does not block interview training.
7. An Interview Plan and an Interview Session are different resources with different state machines.
8. A Session can start only from an approved plan and must retain the approved plan snapshot.
9. Planned questions and scoring rubrics remain hidden during plan review; the user reviews strategy, coverage, duration, and risk focus.
10. Answer evaluation may run during the interview, but scores and feedback are displayed only in the completed report.
11. LLM output is structured and validated. Invalid output cannot be persisted as a successful business result.
12. Celery work uses run/revision ownership so retries and stale workers cannot overwrite newer user decisions.
13. Resume-derived prompts and snapshots contain masked content only and pass PrivacyGuard before external LLM calls.
14. Interview follow-up tasks enter RIP-008 only through an explicit user action with revision-conflict handling.

## 6. PRD Map

| PRD | Draft file | Responsibility | Existing predecessor | Primary downstream dependency |
|---|---|---|---|---|
| JD Import And Library | [jd-import-library-2026-08-05.md](./jd-import-library-2026-08-05.md) | Sources, extraction, review, publishing, immutable JD versions | RIP-003, RIP-007 | Match Assessment |
| Resume-JD Match Assessment | [resume-jd-match-assessment-2026-08-05.md](./resume-jd-match-assessment-2026-08-05.md) | Job Target creation, immutable resume versions, scoring, evidence, report | RIP-002, RIP-003, RIP-007 | Interview Plan, RIP-008 |
| Interview Plan And Scenarios | [interview-plan-scenarios-2026-08-05.md](./interview-plan-scenarios-2026-08-05.md) | Scenario registry, plan generation, strategy review, approval | AIP-001, Match Assessment | Interview Session |
| Interview Runtime And Report | [interview-runtime-report-2026-08-05.md](./interview-runtime-report-2026-08-05.md) | Session orchestration, events, recovery, evaluation, report, follow-up actions | AIP-001, RIP-008, Interview Plan | Later evidence/profile feedback loop |

Dependency order:

```text
Current P0 browser/release closeout
  -> version and minimal Job Target foundation
  -> JD Import And Library increments
  -> Resume-JD Match Assessment
  -> Interview Plan And Scenarios
  -> Interview Runtime And Report
```

The four PRDs are product boundaries, not one-to-one implementation Specs. After approval, each PRD will be decomposed into small end-to-end Specs. New Resume Intelligence slices use the next available `RIP-*` IDs starting at RIP-010; interview slices use the next available `AIP-*` IDs starting at AIP-013. Local issues continue from issue #092.

## 7. Program Scope Boundaries

Included in this program:

- Text-based technical interview preparation and execution.
- Five JD input modes: text, supported files, image OCR, public URL, and manual form.
- Immutable JD and resume input versions.
- Minimal Job Target grouping.
- Evidence-backed multidimensional matching.
- Versioned interview scenarios and approval-gated Interview Plans.
- Recoverable Interview Sessions and evidence-backed reports.
- Explicit handoff of selected report actions to RIP-008 plans.

Excluded from this program:

- Voice, video, avatars, ASR, TTS, and visual behavior scoring.
- Qdrant-backed RAG, broad question banks, reranking, or company/industry web corpora.
- Code-execution Sandbox or system-design whiteboard analysis.
- Automatic application submission, calendars, notifications, or recruitment-pipeline tracking.
- Authentication, multi-tenant ownership, RBAC, billing, or SaaS security claims.
- Automatic mutation of Candidate Profile or a long-term Career Evidence Graph.
- A template marketplace or broad resume-template expansion.

## 8. Delivery Gates

PRD drafting may proceed while the current worktree is being closed out. Production implementation must not start until:

1. RIP-001 issue #038 and the Celery async runtime correction complete review and authorized ship steps.
2. The running worker and beat processes have been restarted with the corrected runtime lifecycle.
3. RIP-007 and RIP-008 browser-required acceptance has been completed or an explicit release decision records the remaining blocker.
4. The current AIP-001 text interview path has a browser baseline covering create, answer, follow-up, completion, and report.
5. The four PRDs in this program are reviewed and confirmed.
6. `/prd-to-spec` records the stable domain, database, API, backend, frontend, migration, privacy, and compatibility decisions.
7. `/to-issues` creates dependency-aware issues small enough for one `/goal` run.

## 9. Program Success Criteria

- Every requirement in the 2026-08-05 workflow source maps to one PRD acceptance criterion, a named non-goal, or a documented later phase.
- No PRD creates a second implementation of the current JD library, matching engine, job-search plan, LLM gateway, privacy guard, or interview workflow.
- Historical matches, plans, sessions, and reports remain reproducible after JD or resume edits.
- The browser can complete the main chain without repasting a JD or silently switching input versions.
- Every match conclusion and interview report assertion identifies its evidence source or explicitly states that evidence is insufficient.
- All UI stories cover loading, empty, success, failure, mutation-pending, and applicable conflict/expired states.

## 10. Confirmed Decisions

- The intake and four PRDs are approved for specification; formal Specs and Issue proposals remain separately reviewable before implementation.
- A minimal Job Target is part of the program.
- JD and resume inputs use immutable version resources rather than revision numbers alone.
- Job Target creation happens on the first downstream action.
- Interview Plan review shows strategy and coverage but hides exact questions and rubrics.
- Interview feedback is withheld until the completed report.
- Match scores do not block interview training.
- The first runtime remains text-only and does not activate RAG, Qdrant, Sandbox, or multimodal packages.

## 11. Review Checklist

- [x] Product positioning matches the 2026-08-04 direction.
- [x] The four product boundaries match the 2026-08-05 workflow.
- [x] Shared terms have one meaning across all PRDs.
- [x] Existing capability is correctly classified as baseline rather than new work.
- [x] Scope exclusions match the intended delivery order.
- [x] Versioning, Job Target creation, plan visibility, and feedback timing reflect the confirmed decisions.
- [x] The program is ready to proceed to technical Spec and Issue proposal review.
