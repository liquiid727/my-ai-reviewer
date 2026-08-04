# RIP-006 - Resume AI Assistant

**Status**: Implemented; browser QA pending due environment restriction
**Depends on**: RIP-004, RIP-005
**Scope**: Resume Builder conversational edit proposals

## Goal

Add an AI assistant to the Resume Builder. The assistant uses the active, verified
LLM configuration to turn a user instruction into a structured, reviewable edit
proposal. A proposal never changes the draft until the user selects operations and
applies them.

## Interaction Contract

```text
instruction -> structured proposal -> review selected changes -> apply once
                                                -> reject
                                                -> undo latest applied proposal
```

- The assistant entry is docked at the bottom of the content sidebar.
- The expanded assistant reuses the existing 400px editor panel and is mutually
  exclusive with style, photo, summary, and section panels.
- Desktop keeps the A4 preview visible. Tablet uses an overlaid panel and mobile
  uses a bottom sheet style panel.
- Empty, loading, success, conflict, and failure states are required.

## Domain Contract

`ResumeEditAgent.propose(draft, instruction)` returns an `EditProposal` with an
assistant message, model/usage metadata, and allow-listed operations. Supported
operations are:

- replace summary
- replace an identity text field (`name`, `email`, `phone`, `location`)
- replace an item field (`heading`, `subheading`, `date_range`)
- replace, add, or remove one bullet

Sections and items have stable IDs. Bullet positions are protected by the draft
revision. Photo references, templates, layout policy, design tokens, custom CSS,
status, ownership, and arbitrary JSON paths are never writable by the assistant.

## Consistency Contract

- `resume_drafts.revision` starts at 1 and increments for every draft-content edit.
- Propose and apply requests carry `base_revision`.
- Apply is atomic and returns HTTP 409 when the draft no longer matches the proposal.
- Applying selected operations performs one persistence write and one preview refresh.
- An applied proposal stores its before/after snapshots. Undo is allowed only while
  the draft is still at that proposal's applied revision.
- `client_request_id` makes proposal creation idempotent.

## Persistence

- `resume_edit_sessions`: one conversation for a draft.
- `resume_edit_messages`: ordered user and assistant messages.
- `resume_edit_proposals`: structured operations, status, model usage, snapshots,
  and applied revision.

## LLM Rules

- Reuse the active and verified persisted LLM configuration.
- Resume content is untrusted data and cannot override the system instruction.
- Use one non-streaming structured JSON request for each turn.
- Retry malformed JSON once; never persist partial model output as an edit.
- Limit instruction and output lengths and send only the current structured draft.

## Out of Scope

- Streaming tokens, background jobs, LangGraph, or Celery orchestration
- Multi-user authentication and tenant ownership changes
- Collaborative editing or automatic conflict merging
- AI changes to visual design, photos, or exported files

## Acceptance Criteria

- A verified configured LLM can propose resume edits from the Builder assistant.
- A proposal does not change the draft before explicit application.
- Users can select operations, apply once, reject, and undo an applicable proposal.
- Stale proposals receive a visible conflict state without changing the draft.
- The content list remains scrollable and the assistant stays reachable at the
  sidebar bottom across supported viewports.
- Backend unit tests, frontend lint/build, and browser desktop/mobile checks pass.
