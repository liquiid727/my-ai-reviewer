# Job Target Interview Issue Proposal

**Status**: Pending user review

**Prepared**: 2026-08-05

**Proposed creation mode**: Local files under `specs/issues/` (repository-native; GitHub or iCafe may be selected during confirmation)

**Sources**:

- `spec-draft/job-target-interview-program-2026-08-05.md`
- `design/job-target-interview-architecture.md`
- `specs/RIP-010-job-target-input-versions/spec.md` through `specs/RIP-014-match-report-plan-bridge/spec.md`
- `specs/AIP-013-interview-scenario-registry/spec.md` through `specs/AIP-017-interview-report-history-actions/spec.md`

This document is the `/to-issues` review artifact. It reserves no external identifier and does not create formal local/GitHub issues. After approval, each section will become one `specs/issues/issue-NNN-<slug>.md` file, the relevant Spec `tasks.md` files will be generated, and `specs/issues/README.md` will be updated.

## Global Delivery Gates

All implementation issues are additionally gated by:

- issue #038 and the Celery async runtime correction completing review and authorized ship;
- worker and beat restart with the corrected lifecycle;
- RIP-007/RIP-008 browser acceptance closed or explicitly waived;
- an AIP-001 create/answer/follow-up/report browser baseline;
- this Issue proposal approved for local creation.

These gates are program prerequisites, not repeated as false issue dependencies where no implementation artifact is consumed.

## RIP-010 Job Target And Input Version Foundation

### Issue #092: Add immutable input-version schema and JD v1 backfill

**Description**: Create the append-only JD/Resume Version persistence foundation and safely backfill every existing ready JD as version 1.

**Acceptance Criteria**:

- [ ] Add `job_description_versions` and `resume_versions` with exact source/content/version/privacy constraints from RIP-010.
- [ ] Add indexed foreign keys, source-specific partial uniqueness, score-free immutable snapshot fields, and no update/delete command path.
- [ ] Add `job_descriptions.current_version_id` after the version table exists.
- [ ] Backfill ready JDs as v1 without inventing unavailable evidence or changing mutable source rows.
- [ ] Migration upgrade/downgrade and representative legacy-data tests pass from the actual Alembic head.
- [ ] Update `design/database.md` with as-implemented columns, indexes, compatibility, and rollback notes.

**Dependencies**: issue #038 delivery gate

**Type**: backend / database

**Priority**: high

**PRD Reference**: JD US-005; Match US-002

**SPEC Reference**: RIP-010 sections 6.1/6.2, 10, 11

### Issue #093: Add Job Target schema and active-target invariants

**Description**: Add the minimal Job Target aggregate and enforce one active target per JD identity in the current anonymous scope.

**Acceptance Criteria**:

- [ ] Add `job_targets` with JD/default-version references, revision, timestamps, and archive state.
- [ ] Add the partial unique active-JD index and all foreign-key/list indexes.
- [ ] Implement pure rules for default-version ownership, revision increment, archive, and historical preservation.
- [ ] Prove concurrent inserts cannot leave duplicate active targets.
- [ ] Document that future user/tenant ownership requires a separate migration rather than silently widening this invariant.

**Dependencies**: #092

**Type**: backend / database

**Priority**: high

**PRD Reference**: Match US-001; FR-1 through FR-3

**SPEC Reference**: RIP-010 sections 6.3, 10.3, 11

### Issue #094: Publish and query immutable input versions

**Description**: Implement application-owned publication/query interfaces for exact masked Resume Versions and read-only JD Versions.

**Acceptance Criteria**:

- [ ] Publish or resolve an evaluated parsed resume or exact saved Builder revision without accepting arbitrary client snapshots.
- [ ] Canonicalize/hash input, run PrivacyGuard, and persist masked/profile/evidence snapshots only.
- [ ] Expose typed Resume Version create/list/detail and JD Version list/detail endpoints under `/api/v1`.
- [ ] Make same-source/same-content publication idempotent and detect source-revision races.
- [ ] Cursor queries return summaries without loading full snapshots; detail never returns real-value mappings.
- [ ] Unit/integration/privacy tests cover both source types, not-ready, conflict, not-found, and canary leakage.

**Dependencies**: #092

**Type**: backend

**Priority**: high

**PRD Reference**: Match US-002; JD US-005/006

**SPEC Reference**: RIP-010 sections 6.1/6.2, 7.1/7.2, 9

### Issue #095: Implement Job Target lifecycle commands and API

**Description**: Provide idempotent downstream target creation, revision-safe defaults, archive, and bounded target queries.

**Acceptance Criteria**:

- [ ] `POST /job-targets` ensures an active target and handles uniqueness races by returning the winner.
- [ ] Validate default JD/Resume Version ownership and reject cross-identity tuples.
- [ ] Implement get/list, revision-checked default update, and archive commands through application use cases.
- [ ] Confirm importing, reviewing, publishing, and browsing a JD do not call target ensure.
- [ ] Return safe not-found/archived/revision/scope errors through the shared envelope.
- [ ] Integration tests cover first create, reuse, concurrent create, version switch, conflict, and archive.

**Dependencies**: #093, #094

**Type**: backend

**Priority**: high

**PRD Reference**: Match US-001/002; FR-1 through FR-7

**SPEC Reference**: RIP-010 sections 6.3, 7, 9.1/9.3

### Issue #096: Build Job Target workspace and version selectors

**Description**: Add the minimal Job Target route and reusable immutable-version selectors for downstream flows.

**Acceptance Criteria**:

- [ ] Add `/targets/:id` with job/company/current JD Version/default Resume Version and recent activity summaries.
- [ ] Add typed target/version API modules and types without a second response/error decoder.
- [ ] Let users switch the default Resume Version with revision-conflict recovery.
- [ ] Render loading, empty, success, failure, mutation pending, conflict, and archived states in Chinese and English.
- [ ] Deep-link refresh resolves the requested target and never substitutes the latest target/version silently.
- [ ] Frontend test/lint/build and desktop/mobile browser checks pass.

**Dependencies**: #095

**Type**: frontend / fullstack

**Priority**: high

**PRD Reference**: Match US-001/002; JD US-008

**SPEC Reference**: RIP-010 sections 8, 9, 11

## RIP-011 JD Review And Version Publishing

### Issue #097: Expand JD review schema and extractor evidence

**Description**: Extend JD structured extraction to the complete review schema with stable evidence, confidence, provenance, and strict output validation.

**Acceptance Criteria**:

- [ ] Add all scalar/list/hard-condition fields defined by the JD PRD with bounded Pydantic v2 schemas.
- [ ] Give requirements/responsibilities/skills stable item keys, evidence status, confidence, and provenance.
- [ ] Return null/empty for unknown fields and reject fabricated/unknown evidence references.
- [ ] Save parser/model/prompt/schema versions and overall confidence without raw provider output.
- [ ] Treat embedded source instructions as untrusted data.
- [ ] Synthetic complete/sparse/conflicting/malicious/malformed fixtures pass.

**Dependencies**: #094

**Type**: backend

**Priority**: high

**PRD Reference**: JD US-003; FR-12 through FR-16

**SPEC Reference**: RIP-011 sections 6.1, 7.1, 11

### Issue #098: Add revision-safe JD review-draft workflow

**Description**: Make successful extraction enter an explicit review state and add revision-safe structured editing without changing source text.

**Acceptance Criteria**:

- [ ] Expand JD state/step constraints for `needs_review`, `review`, and safe draft metadata.
- [ ] Finalizers write a review draft only when run ownership remains current.
- [ ] Add `PATCH /jd/{id}/review` with `expected_review_revision` and explicit-clear semantics.
- [ ] Preserve field/item provenance and mark human changes `manual`.
- [ ] Expose current-version usability separately while a ready JD has a processing/review draft.
- [ ] Tests cover concurrent edits, stale runs, manual provenance, invalid evidence, and safe errors.

**Dependencies**: #097

**Type**: backend

**Priority**: high

**PRD Reference**: JD US-002/004; FR-6 through FR-8, FR-15/16

**SPEC Reference**: RIP-011 sections 6.2/6.3, 7.1/7.2, 9.1

### Issue #099: Publish immutable JD versions and history API

**Description**: Add explicit idempotent publication and read-only version history from the reviewed draft.

**Acceptance Criteria**:

- [ ] `POST /jd/{id}/publish` validates the expected review revision and complete canonical snapshot.
- [ ] Insert the immutable version and switch `current_version_id` in one short transaction.
- [ ] Resolve repeated same-content/schema publication to the existing version.
- [ ] Expose cursor history and exact version detail with source/generator/publication metadata.
- [ ] Published rows have no PATCH/delete command and downstream links use `jd_version_id`.
- [ ] Tests prove old version content remains unchanged after later publications.

**Dependencies**: #092, #098

**Type**: backend

**Priority**: high

**PRD Reference**: JD US-005/006; FR-17 through FR-21

**SPEC Reference**: RIP-011 sections 6.2, 7.1, 9, 10

### Issue #100: Add JD reparse, retry, archive, and legacy compatibility

**Description**: Complete the versioned lifecycle around failed/reparsed drafts while preserving current versions and existing callers.

**Acceptance Criteria**:

- [ ] Reparse creates a new run/draft, protects manual fields by default, and never mutates current/history versions.
- [ ] Retry resumes from the latest safe step with a new run ID; broker/timeout failures are durable and safe.
- [ ] Add abandon-draft and archive commands; referenced identities cannot hard-delete.
- [ ] Reparse failure leaves current version usable and visible.
- [ ] Preserve legacy JD endpoints/fields while marking new downstream paths version-pinned.
- [ ] Integration tests cover duplicate, retry, stale worker, archive, referenced delete, and legacy consumers.

**Dependencies**: #099

**Type**: backend

**Priority**: high

**PRD Reference**: JD US-006/007; FR-20 through FR-26, FR-28

**SPEC Reference**: RIP-011 sections 6.2/6.3, 7.2/7.3, 9.3

### Issue #101: Build JD review and version-history UI

**Description**: Upgrade `/jobs/:id` into a recoverable source-vs-structured review and immutable-version history workflow.

**Acceptance Criteria**:

- [ ] Compare read-only source content with structured fields/evidence/confidence in one page-level workflow.
- [ ] Support revision-safe edits, explicit publish, reparse, retry, abandon draft, and archive confirmations.
- [ ] Preserve local edits after save failure and reconcile revision conflicts without silent overwrite.
- [ ] Show draft/current/history states distinctly and open historical versions read-only.
- [ ] Enable downstream actions only with a current version and pass its exact ID.
- [ ] Cover loading/empty/processing/review/ready/failed/archived and desktop/mobile accessibility states.

**Dependencies**: #098, #099, #100

**Type**: frontend / fullstack

**Priority**: high

**PRD Reference**: JD US-004/005/006/008

**SPEC Reference**: RIP-011 sections 8, 9, 11

### Issue #102: Close JD versioning migration and browser acceptance

**Description**: Verify the complete existing-source import -> review -> publish -> version-history chain and record compatibility evidence.

**Acceptance Criteria**:

- [ ] Migration smoke covers legacy ready v1 backfill and new review constraints/indexes.
- [ ] Text/file/URL each reach review, publish, history, reparse failure recovery, and version-pinned downstream action.
- [ ] Duplicate, broker failure, timeout, stale run, referenced archive/delete, and concurrent edit/publish branches pass.
- [ ] Old JD API and RIP-003/RIP-008 compatibility tests remain green.
- [ ] Browser verifies desktop/mobile layouts, refresh persistence, conflicts, and no sensitive/error-object leakage.
- [ ] Required lint/type/test/build/diff gates and traceability evidence are recorded without claiming blocked checks passed.

**Dependencies**: #101

**Type**: fullstack / test

**Priority**: high

**PRD Reference**: JD US-002 through US-008

**SPEC Reference**: RIP-011 sections 10 through 12

## RIP-012 JD Source Expansion

### Issue #103: Add image JD import through the OCR registry

**Description**: Add bounded PNG/JPEG JD import that reuses the shipped RIP-001 OCR parser and enters the versioned review workflow.

**Acceptance Criteria**:

- [ ] Validate extension, MIME, magic bytes, size, dimensions, and decode bounds before storage.
- [ ] Persist JD identity/source object before dispatch and return a run-owned processing state.
- [ ] Resolve OCR through the existing parser registry without importing a provider SDK into JD code.
- [ ] Feed normalized OCR text into duplicate detection and RIP-011 extraction/review.
- [ ] Handle no-text, parser unavailable, timeout, missing object, retry, cleanup, and stale-run paths safely.
- [ ] Synthetic PNG/JPEG unit/integration/storage tests pass.

**Dependencies**: issue #030, #102

**Type**: backend

**Priority**: high

**PRD Reference**: JD US-001/002/007; FR-3, FR-6 through FR-11

**SPEC Reference**: RIP-012 sections 6.1, 7.1/7.2, 9, 11

### Issue #104: Add manual JD source creation

**Description**: Add synchronous structured manual JD creation with honest provenance and mandatory review before publish.

**Acceptance Criteria**:

- [ ] Add `manual` source policy and request schema with title as the only mandatory business field.
- [ ] Validate all optional fields against RIP-011 bounds and canonical structured shape.
- [ ] Persist manual provenance/confidence without fabricating source quotes or calling an LLM.
- [ ] Enter `needs_review`, never auto-publish, and never create a Job Target.
- [ ] Apply canonical duplicate detection and existing archive/reference rules.
- [ ] API/domain tests cover sparse/complete/invalid/duplicate manual entries.

**Dependencies**: #102

**Type**: backend

**Priority**: medium

**PRD Reference**: JD US-001/002; FR-5/6, FR-12 through FR-16, FR-22/23/29

**SPEC Reference**: RIP-012 sections 6.2/6.3, 7.1, 9

### Issue #105: Build five-mode JD import UI

**Description**: Extend the existing JD import dialog to text, file, image, URL, and manual modes through one validated payload interface.

**Acceptance Criteria**:

- [ ] Use a segmented source-mode control with mutually exclusive, type-appropriate inputs.
- [ ] Validate current-mode input and prevent data from an inactive mode entering the request.
- [ ] Show image/file name, type, size and actionable URL/manual validation.
- [ ] Represent processing/review/duplicate/failure/retry states and stop polling on terminal/ownership loss.
- [ ] Keep Chinese/English resources synchronized and errors localized/safe.
- [ ] Component and desktop/mobile browser checks confirm stable layout and no overlap.

**Dependencies**: #103, #104

**Type**: frontend

**Priority**: high

**PRD Reference**: JD US-001/002/008

**SPEC Reference**: RIP-012 sections 8, 9, 11

### Issue #106: Close JD source-expansion acceptance

**Description**: Verify all five sources share one duplicate, review, publish, archive, storage, and recovery contract.

**Acceptance Criteria**:

- [ ] Complete all five source flows through a published JD Version using synthetic inputs.
- [ ] Confirm image uses the existing OCR module and manual mode makes no LLM call.
- [ ] Verify file/object retention and cleanup across duplicate cancel, failure, retry, archive, and stale work.
- [ ] Verify no import mode creates a Job Target before a downstream action.
- [ ] Run migration, backend, frontend, browser, privacy, lint, type, build, and diff gates.
- [ ] Record requirement/test evidence and any environmental blocker accurately.

**Dependencies**: #105

**Type**: fullstack / test

**Priority**: medium

**PRD Reference**: JD US-001/002/007/008

**SPEC Reference**: RIP-012 sections 10 through 12

## RIP-013 Match Assessment Engine

### Issue #107: Implement match-v1 scoring and deterministic gap engine

**Description**: Build the pure versioned scoring policy, Source Catalog normalization, caps, and non-conflicting gap classification.

**Acceptance Criteria**:

- [ ] Define the eight stable dimensions and exact 25/15/20/15/10/5/5/5 weights.
- [ ] Build typed JD/Resume Source Catalog IDs with normalized claims, provenance, confidence, and masked evidence.
- [ ] Implement weighted totals, two-decimal rounding, core-skill 75 cap, severe-years 70 cap, and lowest-cap rule.
- [ ] Treat unknown years/evidence as `evidence_gap` without applying unsupported caps.
- [ ] Produce one primary `capability_gap`, `expression_gap`, `evidence_gap`, or `hard_constraint_risk` per requirement.
- [ ] Policy/alias/threshold fixtures validate at startup and unit tests cover all boundary combinations.

**Dependencies**: #106

**Type**: backend

**Priority**: high

**PRD Reference**: Match US-004/005/006; FR-12 through FR-21

**SPEC Reference**: RIP-013 sections 6.2 through 6.5, 11

### Issue #108: Add constrained semantic evidence matcher

**Description**: Add the LLM-backed semantic classifier as a narrow adapter that can only classify allow-listed evidence for the pure engine.

**Acceptance Criteria**:

- [ ] Define strict Pydantic input/output contracts and application-owned matcher interface.
- [ ] Send only bounded masked Source Catalog items through the existing LLM gateway and PrivacyGuard.
- [ ] Reject unknown evidence IDs, conflicting categories, invalid dimensions, malformed output, and prompt injection.
- [ ] Apply explicit gateway timeout and bounded schema retry without holding a database transaction.
- [ ] Persist no prompt, completion, raw provider response, API key, or unmasked resume content.
- [ ] Deterministic fake and gateway-spy tests cover success, insufficient evidence, malicious, timeout, and invalid-output branches.

**Dependencies**: #107

**Type**: backend

**Priority**: high

**PRD Reference**: Match US-005/006; FR-17 through FR-22, FR-28

**SPEC Reference**: RIP-013 sections 6.2/6.4, 7.1, 8

### Issue #109: Add Match Assessment schema and lifecycle

**Description**: Create the version-pinned Match Assessment aggregate with immutable completion, active-run uniqueness, and safe failure state.

**Acceptance Criteria**:

- [ ] Add `match_assessments` with target/version/policy/run/result/generator/failure fields and valid status/score/confidence checks.
- [ ] Index all foreign keys, completed-reuse lookup, target history, active watchdog, and partial active tuple uniqueness.
- [ ] Implement `queued/evaluating/completed/failed` transitions and completed immutability.
- [ ] Define normal reuse, force-new-row, failed retry, and stale-run rules.
- [ ] Reject target/version scope mismatches and deletion of referenced versions.
- [ ] Migration/domain/index tests pass from the current head.

**Dependencies**: #092, #093, #107

**Type**: backend / database

**Priority**: high

**PRD Reference**: Match US-003; FR-7 through FR-11, FR-22

**SPEC Reference**: RIP-013 sections 6.1, 7.2, 10

### Issue #110: Build Match Assessment worker and API

**Description**: Orchestrate idempotent create/reuse, async evaluation, retry, and public status/result queries.

**Acceptance Criteria**:

- [ ] `POST /match-assessments` validates exact versions and ensures/validates the active Job Target.
- [ ] Return a reused completed assessment or persist `queued` and dispatch after commit.
- [ ] Worker builds catalog, applies deterministic/semantic stages, and finalizes only under current run ownership.
- [ ] Broker failure, dependency timeout, invalid evidence, terminal failure, and explicit retry persist safe state.
- [ ] Add cursor list, detail, and retry endpoints with public immutable result schemas.
- [ ] Integration tests cover reuse, force, active duplicate, retry, stale worker, and low-score eligibility.

**Dependencies**: #108, #109

**Type**: backend

**Priority**: high

**PRD Reference**: Match US-003; FR-7 through FR-11, FR-23 through FR-26

**SPEC Reference**: RIP-013 sections 7, 9

### Issue #111: Close match-engine privacy and replay acceptance

**Description**: Verify scoring correctness, evidence integrity, replay behavior, worker convergence, and privacy as one backend acceptance gate.

**Acceptance Criteria**:

- [ ] Maintained synthetic fixtures cover all dimensions, caps, four gap classes, unknown evidence, and score bands.
- [ ] Same versions/policy/fake semantic output replay to the same score, caps, gaps, and explanations.
- [ ] Gateway spies and database/log/API checks contain no unmasked/direct-identifier canaries.
- [ ] Broker failure, timeout, malformed output, retry, concurrent force, and stale-worker cases converge safely.
- [ ] Representative list/reuse queries use expected indexes and bounded query counts.
- [ ] Migration, unit, integration, lint, type, privacy, and diff gates are recorded.

**Dependencies**: #110

**Type**: backend / test

**Priority**: high

**PRD Reference**: Match US-003 through US-006

**SPEC Reference**: RIP-013 sections 10 through 12

## RIP-014 Match Report And Plan Bridge

### Issue #112: Pin RIP-008 plans to versions and assessment

**Description**: Extend RIP-008 plan creation/generation to retain the exact Job Target, input versions, and Match Assessment without changing existing task behavior.

**Acceptance Criteria**:

- [ ] Add nullable indexed restrictive FKs for target/JD Version/Resume Version/Assessment.
- [ ] Add version-pinned unfinished-plan uniqueness while preserving legacy uniqueness semantics.
- [ ] Validate one coherent tuple and build plan Source Catalog from immutable snapshots.
- [ ] Keep legacy plan list/detail/edit/regenerate working with `input_contract=legacy` and null version refs.
- [ ] Regeneration of a version-pinned plan retains its original versions unless a new plan is explicitly created.
- [ ] RIP-008 run/revision/manual-task/progress and migration regression tests pass.

**Dependencies**: issue #057, #111

**Type**: backend / database

**Priority**: high

**PRD Reference**: Match US-008; FR-27

**SPEC Reference**: RIP-014 sections 6.2, 7.2, 9, 10

### Issue #113: Build Match Assessment report projection and actions API

**Description**: Expose a completed Assessment as an evidence-backed report with exact versions, caps, gaps, staleness, and downstream action eligibility.

**Acceptance Criteria**:

- [ ] Build one bounded report projection over assessment, versions, target, and action eligibility without a second report store.
- [ ] Return pre/post-cap totals, eight dimensions, four gap classes, evidence sufficiency, policy/model metadata, and explicit unknowns.
- [ ] Mark newer current/default versions as an advisory stale condition without substituting inputs.
- [ ] Expose target assessment history with stable cursor ordering and no N+1.
- [ ] Keep low-score Interview Plan and RIP-008 actions enabled.
- [ ] API tests cover not-complete, stale, unknown evidence, legacy match separation, and safe public fields.

**Dependencies**: #110, #112

**Type**: backend

**Priority**: high

**PRD Reference**: Match US-007/008; FR-23 through FR-27

**SPEC Reference**: RIP-014 sections 6.1/6.3, 7.1/7.3, 9

### Issue #114: Build unified match creation and report UI

**Description**: Make JD, resume, matching-center, and Job Target entry points converge on one version-pinned creation/report workflow.

**Acceptance Criteria**:

- [ ] Add typed Match Assessment API/types and target match routes.
- [ ] Preselect source-context versions but allow explicit ready-version switching before submit.
- [ ] Represent loading, empty, queued, evaluating, completed, failed, timeout, retry, stale, and mutation-pending states.
- [ ] Render score dimensions, caps, gaps, evidence sufficiency, and advisory wording without overstating unknown evidence.
- [ ] Provide explicit resume optimization, RIP-008 plan, and Interview Plan actions; low score never disables interview action.
- [ ] Chinese/English, component, build/lint, deep-link, and desktop/mobile browser checks pass.

**Dependencies**: #096, #113

**Type**: frontend / fullstack

**Priority**: high

**PRD Reference**: Match US-001/003/007/008

**SPEC Reference**: RIP-014 sections 8, 9, 11

### Issue #115: Close target-to-report-to-plan match acceptance

**Description**: Verify the complete Job Target -> Assessment -> report -> RIP-008/Interview Plan entry chain and trace all Match PRD requirements.

**Acceptance Criteria**:

- [ ] Exercise first target creation, version selection, async assessment, evidence report, and plan handoff end to end.
- [ ] Verify completed reuse, force re-evaluate, stale advisory, conflict, timeout, retry, and low-score training.
- [ ] Verify version-pinned RIP-008 plan generation/regeneration remains reproducible and legacy plans remain compatible.
- [ ] Browser validates all four entry points, refresh persistence, mobile layout, safe errors, and no version substitution.
- [ ] Query-count/index and privacy canary checks pass.
- [ ] Required gates and complete Match US/FR-to-test traceability are recorded.

**Dependencies**: #111, #114

**Type**: fullstack / test

**Priority**: high

**PRD Reference**: Match US-001 through US-008

**SPEC Reference**: RIP-014 sections 10 through 12

## AIP-013 Interview Scenario Registry

### Issue #116: Add versioned Interview Scenario registry

**Description**: Add one validated code-backed registry and read API for all seven first-release scenarios.

**Acceptance Criteria**:

- [ ] Define exact scenario/stage/budget/follow-up/skip/scoring value objects and registry interface.
- [ ] Add seven version-1 fixtures with stage weights totaling 100.
- [ ] Enforce durations 15/30/45/60, question/follow-up budgets, depth 2, skip limits, candidate-question bounds, difficulty, and language.
- [ ] Fail deterministically on duplicate/invalid fixture data rather than falling back.
- [ ] Expose list/detail/version endpoints with public policy only and synchronized frontend types/i18n.
- [ ] Unit/API/type tests prove prompts/questions/signals/rubrics are absent.

**Dependencies**: issue #038 delivery gate

**Type**: backend

**Priority**: high

**PRD Reference**: Plan US-002; FR-5 through FR-10

**SPEC Reference**: AIP-013 sections 6 through 12

## AIP-014 Interview Plan Approval

### Issue #117: Add Interview Plan schema and state machine

**Description**: Create the version-pinned Interview Plan aggregate with separate public/private snapshots and immutable approval semantics.

**Acceptance Criteria**:

- [ ] Add `interview_plans` with target/version/assessment/scenario/config, run/revision/state, public/private, hash, and safe failure fields.
- [ ] Index all FKs, target history, review/active run, and supersession paths.
- [ ] Implement valid generating/review/approved/rejected/failed/superseded transitions.
- [ ] Approved is immutable; regeneration creates a linked replacement row.
- [ ] Define public strategy/Coverage Matrix and private question/signal/rubric schemas separately.
- [ ] Migration/domain/serialization tests pass and no private serializer can be constructed accidentally.

**Dependencies**: #111, #116

**Type**: backend / database

**Priority**: high

**PRD Reference**: Plan US-001/005/006; FR-1 through FR-3, FR-11/12, FR-18 through FR-28

**SPEC Reference**: AIP-014 sections 6.1 through 6.4, 10

### Issue #118: Build evidence-constrained Interview Plan generator

**Description**: Generate bounded public/private plan snapshots from exact inputs, Match evidence, and one scenario fixture.

**Acceptance Criteria**:

- [ ] Build a bounded Source Catalog from immutable JD/Resume Versions and the completed Assessment.
- [ ] Call the existing LLM gateway through a typed plan-generator adapter and PrivacyGuard.
- [ ] Validate scenario stages, duration question/follow-up budgets, coverage, evidence allow-list, difficulty, and language.
- [ ] Require high-importance/high-risk coverage or a safe duration-based omission reason.
- [ ] Reject unknown evidence, private/public field leakage, malformed output, and embedded prompt instructions.
- [ ] Fixture/fake/gateway-spy tests cover seven scenarios and all option sets without RAG.

**Dependencies**: #107, #117

**Type**: backend

**Priority**: high

**PRD Reference**: Plan US-003/004; FR-13 through FR-20

**SPEC Reference**: AIP-014 sections 6.2 through 6.4, 7.1, 8

### Issue #119: Build Interview Plan lifecycle worker and API

**Description**: Add async create/retry and revision-safe approve/reject/regenerate commands with public-only queries.

**Acceptance Criteria**:

- [ ] Validate one target/version/assessment/scenario tuple and allow every completed match score.
- [ ] Persist `generating`, dispatch after commit, and finalize only under current run/state ownership.
- [ ] Add create/list/detail/retry/approve/reject/regenerate endpoints and safe action flags.
- [ ] Enforce expected revision, approved immutability, linked regeneration, and broker/timeout failure behavior.
- [ ] Public DTOs contain no exact question, expected signal, rubric, private evidence, prompt, or provider output.
- [ ] Integration tests cover tuple mismatch, low score, retry, conflict, stale worker, and failed regeneration.

**Dependencies**: #118

**Type**: backend

**Priority**: high

**PRD Reference**: Plan US-001/005/006; FR-1 through FR-4, FR-11/12, FR-20 through FR-28

**SPEC Reference**: AIP-014 sections 7, 9

### Issue #120: Build Interview Plan create and review UI

**Description**: Add one creation flow and public strategy review route without exposing private plan data.

**Acceptance Criteria**:

- [ ] Add target input/version/assessment and scenario/duration/difficulty/language selectors.
- [ ] Enter from JD, Resume, Match report, and Job Target with valid preselection and explicit switching.
- [ ] Poll generation safely and render loading/empty/failure/timeout/retry/conflict/stale states.
- [ ] Show stages, objectives, coverage, risk focus, budgets, and duration; never store/render private question/rubric fields.
- [ ] Support revision-safe approve, reject, and regenerate with clear confirmations/recovery.
- [ ] Chinese/English, component, build/lint, deep-link, desktop/mobile, and accessibility checks pass.

**Dependencies**: #114, #116, #119

**Type**: frontend / fullstack

**Priority**: high

**PRD Reference**: Plan US-001/002/005/006/007

**SPEC Reference**: AIP-014 sections 8, 9, 11

### Issue #121: Close Interview Plan privacy and concurrency acceptance

**Description**: Verify plan generation/review/approval across all scenarios while proving private fields never cross transport/browser boundaries.

**Acceptance Criteria**:

- [ ] Exercise seven scenarios, four durations, three difficulties, two languages, coverage omissions, and low-score eligibility.
- [ ] Verify create/retry/approve/reject/regenerate, revision races, broker failure, timeout, and stale workers.
- [ ] Scan API responses, frontend state, logs, fixtures, and screenshots for private-plan/evaluation/privacy canaries.
- [ ] Verify approved snapshot immutability and one explicit Session-create action without automatic Session creation.
- [ ] Browser covers all entry points, refresh, mobile layout, conflict and recovery states.
- [ ] Required gates and complete Plan US/FR traceability are recorded.

**Dependencies**: #120

**Type**: fullstack / test

**Priority**: high

**PRD Reference**: Plan US-001 through US-007

**SPEC Reference**: AIP-014 sections 10 through 12

## AIP-015 Interview Session State And Events

### Issue #122: Evolve interviews into the v2 Session aggregate

**Description**: Extend the existing `interviews` persistence root for plan-driven v2 Sessions while preserving all legacy AIP-001 rows/routes.

**Acceptance Criteria**:

- [ ] Add `contract_version`, approved-plan reference, revision, Session/turn/report states, activity/expiry, current question, ownership, and safe failure fields.
- [ ] Add valid state/check constraints, all foreign-key/cursor/watchdog indexes, and partial one-non-cancelled-Session-per-plan uniqueness.
- [ ] Define pure v2 Session transition/guard rules and exact legacy/v2 serializer dispatch.
- [ ] Backfill existing rows as contract version 1 without synthesizing plan/events/coverage.
- [ ] Prove legacy `/interview` create/start/answer/status/report/list behavior remains unchanged.
- [ ] Migration upgrade/downgrade and representative v1/v2 model tests pass.

**Dependencies**: #121

**Type**: backend / database

**Priority**: high

**PRD Reference**: Runtime US-001/005; FR-1 through FR-5, FR-18/19, FR-21 through FR-24

**SPEC Reference**: AIP-015 sections 6.1/6.2, 8, 10.1/10.4

### Issue #123: Add Session events and Coverage projection

**Description**: Add atomic monotonic Session events and a mutable per-Session copy of approved plan coverage.

**Acceptance Criteria**:

- [ ] Create `interview_events` with unique Session sequence and allow-listed payload schemas per event type.
- [ ] Create `interview_session_coverage` with unique coverage key, status/evidence counts, and indexed references.
- [ ] Copy approved plan coverage on Session creation without mutating plan rows.
- [ ] Update Session state/coverage/event in one root-locked transaction with stable child lock order.
- [ ] Exclude text, score, feedback, prompt, completion, credentials, and replacement maps from all event payloads.
- [ ] Tests cover sequence races, rollback, projection rebuild, payload rejection, and query indexes.

**Dependencies**: #122

**Type**: backend / database

**Priority**: high

**PRD Reference**: Runtime US-007; FR-25 through FR-28, FR-36

**SPEC Reference**: AIP-015 sections 6.3/6.4, 7.1, 10.2/10.3

### Issue #124: Create Sessions from approved plans and start idempotently

**Description**: Implement idempotent v2 Session creation and start from an immutable approved Interview Plan.

**Acceptance Criteria**:

- [ ] `POST /interview-sessions` accepts only plan ID and copies exact approved snapshot references.
- [ ] Repeated/concurrent create returns the existing non-cancelled Session; rejected/failed/unapproved plans are refused.
- [ ] Idempotent start persists/returns one first public question and writes ordered start/question events.
- [ ] Start never returns the remaining private plan or hidden signals/rubrics.
- [ ] Set revision/activity/expiry/current-question fields in short atomic transactions.
- [ ] Integration tests cover duplicate create/start, cancelled replacement, invalid plan, and private-field absence.

**Dependencies**: #119, #122, #123

**Type**: backend

**Priority**: high

**PRD Reference**: Runtime US-001; FR-1 through FR-5

**SPEC Reference**: AIP-015 sections 6.1/6.2, 7.2, 9

### Issue #125: Add Session lifecycle control commands

**Description**: Add revision-safe pause, resume, skip, cancel, and terminate behavior under scenario and terminal-state rules.

**Acceptance Criteria**:

- [ ] Pause/resume preserve the same persisted current question and update active-time/expiry state.
- [ ] Pause during evaluating records `pause_requested`; finalization cannot expose a new active turn.
- [ ] Skip is allowed only before an accepted answer and within exact scenario allowance, with coverage/event updates.
- [ ] Cancel is start-only; terminate is post-start and preserves terminal `terminated` status.
- [ ] Every command requires expected revision, is idempotent where appropriate, and rejects expired/terminal/stale state.
- [ ] Transition/concurrency/integration tests cover every command and conflict pair.

**Dependencies**: #116, #124

**Type**: backend

**Priority**: high

**PRD Reference**: Runtime US-005/006; FR-18 through FR-24

**SPEC Reference**: AIP-015 sections 6.2, 7.3, 9

### Issue #126: Add Session expiry, history, and timeline queries

**Description**: Add 30-day inactivity reconciliation and bounded list/detail/timeline projections for recovery and history.

**Acceptance Criteria**:

- [ ] Compute/extend `expires_at` from accepted user commands and reject post-expiry mutations.
- [ ] Add lazy single-resource reconciliation and Celery Beat batch watchdog without silent requeue/report generation.
- [ ] Add cursor list filters for target/scenario/status and detail action flags/current question/progress.
- [ ] Add cursor timeline over allow-listed events and no transcript/private-plan load.
- [ ] Batch/JOIN report/plan/target summaries without per-Session N+1.
- [ ] Tests cover deadline boundary, watchdog race, deep cursor ordering, expired recovery action, and query counts.

**Dependencies**: #123, #125

**Type**: backend

**Priority**: medium

**PRD Reference**: Runtime US-005/006/010; FR-23/24/28/35/36

**SPEC Reference**: AIP-015 sections 7.4, 8, 9, 10

### Issue #127: Build Session history and live recovery shell

**Description**: Add v2 Session list and live routes that recover server state and expose lifecycle controls before answer execution is connected.

**Acceptance Criteria**:

- [ ] Add `/interview-sessions` and `/interview-sessions/:id` with typed resource clients.
- [ ] List target, scenario, versions, status, progress, activity, and report summary with correct recovery action.
- [ ] Restore exact deep-linked current question/progress after refresh and never replace it with a newer Session.
- [ ] Implement start/pause/resume/skip/cancel/terminate controls with revision conflict/expiry reconciliation.
- [ ] Render loading, empty, failure, mutation pending, retryable, conflict, cancelled, terminated, expired, and legacy-link states.
- [ ] Chinese/English, component, build/lint, desktop/mobile, and stable-dimension layout checks pass.

**Dependencies**: #124, #126

**Type**: frontend / fullstack

**Priority**: high

**PRD Reference**: Runtime US-001/005/010

**SPEC Reference**: AIP-015 sections 8, 9, 11

### Issue #128: Close Session state and compatibility acceptance

**Description**: Verify v2 Session state/events/recovery/expiry and prove v1 AIP-001 compatibility before adding turn execution.

**Acceptance Criteria**:

- [ ] Exercise create/start/pause/resume/skip/cancel/terminate/expiry and all revision/idempotency races.
- [ ] Verify event monotonicity/allow-list/rollback and relational projection recovery after checkpoint mismatch.
- [ ] Verify one non-cancelled Session per plan and stale worker cannot reopen terminal state.
- [ ] Run legacy v1 API/browser regression with representative existing rows/reports.
- [ ] Browser verifies deep links, multiple tabs, refresh, mobile controls, conflicts, expiry, and no private payload leakage.
- [ ] Migration, backend, frontend, privacy, query, lint, type, build, and traceability evidence are recorded.

**Dependencies**: #125, #127

**Type**: fullstack / test

**Priority**: high

**PRD Reference**: Runtime US-001/005/006/007/010

**SPEC Reference**: AIP-015 sections 10 through 12

## AIP-016 Coverage-Driven Interview Runtime

### Issue #129: Implement deterministic coverage and follow-up policies

**Description**: Implement pure stage, coverage, time, follow-up, candidate-question, and skip decision rules.

**Acceptance Criteria**:

- [ ] Select eligible Coverage Items by exact deterministic importance/sufficiency/asked/risk/key ordering.
- [ ] Respect scenario stage order, question/follow-up/depth/time budgets, skip status, and planned counts.
- [ ] Advance stage or mark `not_reached` with safe reasons when coverage/time ends.
- [ ] Trigger follow-up only for vague/shallow/contradictory/missing evidence and stop on sufficient evidence/depth/budget.
- [ ] Support 1-3 candidate questions where the scenario allows and prohibit invented internal-company facts.
- [ ] Pure fixture tests cover ties, no time, all statuses, seven scenarios, and boundary budgets.

**Dependencies**: #116, #123

**Type**: backend

**Priority**: high

**PRD Reference**: Runtime US-002/004/006; FR-6 through FR-10, FR-16/17/20

**SPEC Reference**: AIP-016 sections 6.1/6.2, 11

### Issue #130: Build the plan-driven v2 LangGraph

**Description**: Add a v2 workflow that orchestrates one planned question/follow-up at a time through application interfaces.

**Acceptance Criteria**:

- [ ] Add separate v2 state/graph/nodes without changing the legacy AIP-001 graph.
- [ ] Keep deterministic Orchestrator separate from LLM Interviewer and evidence projection.
- [ ] Load exact approved plan/scenario/current coverage and persist no state directly from nodes.
- [ ] Generate/reveal one question with stage/coverage/parent links and bounded private evidence.
- [ ] Preserve relational state as authority and repair/rebuild checkpoint state safely.
- [ ] Graph/node tests cover question, follow-up, stage transition, pause, finish, and checkpoint mismatch.

**Dependencies**: #118, #124, #129

**Type**: backend

**Priority**: high

**PRD Reference**: Runtime US-002/004; FR-6 through FR-10, FR-14, FR-16/17, FR-28

**SPEC Reference**: AIP-016 sections 6.1/6.2, 7.1, 8

### Issue #131: Persist hidden Answer Evaluations

**Description**: Separate v2 Answer Evaluation from the accepted masked answer and constrain evaluator evidence/output.

**Acceptance Criteria**:

- [ ] Create `answer_evaluations` with unique answer relationship, scores/signals/evidence/confidence/follow-up/coverage fields and indexes.
- [ ] Define strict evaluator schema and application-owned adapter using the existing LLM gateway.
- [ ] Accept only known question/coverage/source evidence IDs and reject numeric/schema disagreement.
- [ ] Keep external calls transaction-free with timeout and PrivacyGuard.
- [ ] Ensure v2 answers never write legacy score/feedback/raw-response columns.
- [ ] Migration/unit/gateway-spy tests cover normal, insufficient, malformed, malicious, timeout, and privacy rejection.

**Dependencies**: #122, #130

**Type**: backend / database

**Priority**: high

**PRD Reference**: Runtime US-003/007; FR-12 through FR-15, FR-25, FR-36

**SPEC Reference**: AIP-016 sections 6.2/6.3, 8, 10

### Issue #132: Build the durable idempotent answer turn

**Description**: Add answer acceptance, async evaluation/next-turn worker, polling projection, retry, timeout, and stale-run convergence.

**Acceptance Criteria**:

- [ ] Require current question, expected revision, and `Idempotency-Key`; same key/payload reuses, mismatched payload conflicts.
- [ ] Mask direct identifiers, run PrivacyGuard, persist masked answer, set evaluating, write event, and commit before dispatch.
- [ ] Worker evaluates/generates outside transaction and finalizes evaluation/coverage/next question/events only under current ownership.
- [ ] Enforce 180-second deadline, bounded transient retry, broker failure, watchdog retryable state, and explicit user retry.
- [ ] Respect pause request/terminate/expiry and prevent stale worker terminal-state rewrites.
- [ ] API responses/live projections contain no evaluation score, feedback, signal, rubric, or private-plan fields.

**Dependencies**: #125, #131

**Type**: backend

**Priority**: high

**PRD Reference**: Runtime US-003/005/006; FR-11 through FR-20, FR-23/24/27/28

**SPEC Reference**: AIP-016 sections 6.3/6.4, 7.2 through 7.4, 9

### Issue #133: Build the live v2 interview UI

**Description**: Connect the Session page to durable answer turns while preserving interview rhythm and withholding feedback.

**Acceptance Criteria**:

- [ ] Add stable current-question, masked answer editor, stage/progress, pending state, and lifecycle control regions.
- [ ] Submit once with idempotency/revision, disable duplicates, and poll until ready/retryable/terminal.
- [ ] Handle follow-up, skip, pause/resume, terminate, retryable failure, conflict, expiry, refresh, and ownership cleanup.
- [ ] Do not place score/feedback/rubric/private-plan data in API types, store, DOM, toast, or browser history.
- [ ] Keep input/control dimensions stable across long text, pending/error, desktop/mobile, and localization.
- [ ] Component, build/lint, deep-link, keyboard/accessibility, and real browser checks pass.

**Dependencies**: #127, #132

**Type**: frontend / fullstack

**Priority**: high

**PRD Reference**: Runtime US-001 through US-006

**SPEC Reference**: AIP-016 sections 8, 9, 11

### Issue #134: Close runtime recovery and privacy acceptance

**Description**: Verify the complete plan-driven text interview through coverage completion under retries, restarts, concurrency, and privacy constraints.

**Acceptance Criteria**:

- [ ] Exercise stage/coverage/follow-up/time/skip/candidate-question branches across representative scenarios.
- [ ] Verify duplicate answers/tabs, broker failure, timeout, watchdog, explicit retry, pause request, terminate, expiry, and stale workers.
- [ ] Restart API/worker/checkpointer and recover the same current question with no duplicate answer/evaluation/event.
- [ ] Scan DB, events, logs, responses, frontend state, fixtures, and screenshots for raw identifiers/private evaluation canaries.
- [ ] Browser validates full desktop/mobile flow and no live score/feedback exposure.
- [ ] Migration, unit, integration, worker, privacy, frontend, lint, type, build, diff, and traceability gates are recorded.

**Dependencies**: #128, #133

**Type**: fullstack / test

**Priority**: high

**PRD Reference**: Runtime US-001 through US-007

**SPEC Reference**: AIP-016 sections 10 through 12

## AIP-017 Interview Report, History And Actions

### Issue #135: Build evidence-backed report aggregation model

**Description**: Define deterministic complete/incomplete report aggregation and immutable report/recommendation persistence.

**Acceptance Criteria**:

- [ ] Aggregate seven report dimensions from persisted evaluations using scenario policy weights.
- [ ] Compute completion/answered/skipped/not-reached and JD Coverage summaries from relational projections.
- [ ] Require every strength/risk/recommendation evidence ID or explicit `insufficient_evidence`.
- [ ] Extend v2 report persistence with kind, coverage/evidence/policy/hash metadata and immutable content.
- [ ] Add separate recommendation rows with stable key/content and mutable apply metadata.
- [ ] Migration/domain tests cover complete, terminated incomplete, zero-answer ineligible, and legacy report labeling.

**Dependencies**: #132, #134

**Type**: backend / database

**Priority**: high

**PRD Reference**: Runtime US-008; FR-29 through FR-31, FR-36

**SPEC Reference**: AIP-017 sections 6.1 through 6.3, 10

### Issue #136: Build complete/incomplete report worker and lifecycle

**Description**: Generate constrained report prose/recommendations asynchronously without recomputing scores or changing terminated status.

**Acceptance Criteria**:

- [ ] Dispatch normal complete and eligible terminated-incomplete reports with separate report run/status.
- [ ] Build bounded relational aggregate and call report writer outside transaction.
- [ ] Reject unknown evidence/recommendation keys, dimension disagreement, malformed output, and privacy leakage.
- [ ] Finalize one immutable report only under current run/status; normal completing Session becomes completed, terminated remains terminated.
- [ ] Persist safe failure/retryability, support explicit retry without re-evaluation, and block stale overwrite.
- [ ] Worker/integration tests cover broker failure, timeout, retry, duplicate task, stale run, and zero-answer behavior.

**Dependencies**: #135

**Type**: backend

**Priority**: high

**PRD Reference**: Runtime US-008; FR-22, FR-29 through FR-31

**SPEC Reference**: AIP-017 sections 7.1/7.3, 8

### Issue #137: Apply report recommendations to RIP-008

**Description**: Preview and apply selected recommendations through existing revision-checked manual-task commands with partial-result reconciliation.

**Acceptance Criteria**:

- [ ] Preview validates recommendation/plan/Job Target tuple and returns proposed task fields without mutation.
- [ ] Apply processes stable recommendation order and calls the RIP-008 application command, never its tables directly.
- [ ] Persist task mapping atomically with each successful plan revision mutation.
- [ ] Already-applied recommendations are idempotent successes and never duplicate tasks.
- [ ] Return all-success, zero-success conflict, and 207 partial applied/failed/not-attempted results with latest revision.
- [ ] Integration tests cover cancel, all success, repeated apply, mid-batch conflict, plan mismatch, and safe failure.

**Dependencies**: #112, #136

**Type**: backend

**Priority**: high

**PRD Reference**: Runtime US-009; FR-32 through FR-34

**SPEC Reference**: AIP-017 sections 6.3/6.4, 7.4, 9

### Issue #138: Build report, history, and timeline projections

**Description**: Expose immutable report detail, report retry, recommendation state, and bounded Session/history/timeline queries.

**Acceptance Criteria**:

- [ ] Add Session report status/detail and report-by-ID endpoints with complete/incomplete/insufficient semantics.
- [ ] Add report retry command and recommendation preview/apply endpoints with safe public schemas.
- [ ] Add cursor Session history filters and timeline projection with report summary/recovery actions.
- [ ] JOIN/batch target/plan/report/recommendation summaries without transcript/private-plan/full-report N+1 loads.
- [ ] Keep v1 legacy reports on legacy routes and clearly label their contract.
- [ ] API/query tests cover waiting/failure/retry/complete/incomplete/partial apply/cursor and private-field absence.

**Dependencies**: #123, #136, #137

**Type**: backend

**Priority**: high

**PRD Reference**: Runtime US-008/010; FR-29 through FR-36

**SPEC Reference**: AIP-017 sections 7.2, 8, 9

### Issue #139: Build interview report and history UI

**Description**: Add evidence-first report and high-density history views with explicit recommendation application/reconciliation.

**Acceptance Criteria**:

- [ ] Add `/interview-sessions/:id/report` and complete history filtering/recovery links.
- [ ] Show completion kind, dimensions, JD Coverage, evidence-backed strengths/risks, and insufficient-evidence labels with accessible text alternatives.
- [ ] Render waiting/failed/retry/complete/incomplete/zero-answer and legacy states accurately.
- [ ] Preview selected recommendations, confirm target RIP-008 plan, apply, and reconcile success/partial/conflict without losing selection.
- [ ] Keep report content immutable in UI and show applied task links as separate metadata.
- [ ] Chinese/English, component, build/lint, deep-link, desktop/mobile, accessibility, and no-overlap browser checks pass.

**Dependencies**: #138

**Type**: frontend / fullstack

**Priority**: high

**PRD Reference**: Runtime US-008/009/010

**SPEC Reference**: AIP-017 sections 8, 9, 11

### Issue #140: Close the full Job Target interview program runtime

**Description**: Execute and document the complete JD Version -> Resume Version -> Target -> Match -> approved Plan -> Session -> report -> RIP-008 action chain.

**Acceptance Criteria**:

- [ ] Run the full synthetic user journey without repasting JD or silently switching any input version.
- [ ] Verify normal complete and terminated-incomplete reports, recovery/retry/conflict/expiry, and recommendation partial reconciliation.
- [ ] Prove historical match/plan/session/report meaning remains unchanged after newer JD/Resume versions.
- [ ] Prove live API/browser state contains no score/feedback/rubric and all report claims have evidence or insufficiency markers.
- [ ] Verify legacy JD/plan/AIP-001 contracts remain usable and planned RAG/Qdrant/voice/Sandbox packages remain inactive.
- [ ] Run migration smoke, backend unit/integration, frontend tests/lint/build, browser desktop/mobile, privacy, architecture, diff, and standardized result evidence.
- [ ] Complete PRD -> Spec -> Issue -> test/review traceability and record any remaining release blocker without shipping automatically.

**Dependencies**: #137, #139

**Type**: fullstack / test

**Priority**: high

**PRD Reference**: Runtime US-001 through US-010 and program success criteria

**SPEC Reference**: AIP-017 sections 10 through 12; all program Specs

## Review Instructions

Review the dependency order, Issue size, ownership type, and acceptance boundaries. Confirm both the list and creation mode before Issue creation. Commit, push, PR, merge, issue closure, production migration, service restart, and release remain separate actions.
