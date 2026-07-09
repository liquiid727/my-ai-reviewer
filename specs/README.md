# SpecOS Specs

`specs/` is the feature-spec layer of SpecOS.

The canonical structure is:

```text
specs/
  roadmap.md
  _draft/
  _rules/
  _template/
  RP-001-event-ingestion/
    spec.md
  RP-002-decision-api/
    spec.md
  ...
```

## Directory Meaning

- `roadmap.md`: the only canonical epic, release, order, and dependency index
- `_draft/`: optional intake holding area for feature ideas that are not ready to become active specs
- `_rules/`: spec naming, slicing, and field conventions
- `_template/`: canonical spec templates
- `RP-xxx-<slug>/spec.md`: one small feature spec per directory

Epic grouping does not become a nested directory structure. Keep feature specs flat by spec id and use `roadmap.md` plus spec metadata to express epic membership and ordering.

## Lifecycle

```text
spec-draft/
  -> design/<platform>-design.md
  -> specs/roadmap.md
  -> specs/<SPEC-ID>-<slug>/spec.md
  -> implementation/<SPEC-ID>-<slug>/
  -> reviews/<SPEC-ID>-<slug>/
  -> tests/
```

## Feature Spec Rules

- One feature spec = one reviewable feature slice
- Prefer narrow slices like `Decision API`, not broad buckets like `Decision Engine`
- Dependencies must be listed by spec id
- Prerequisites must list upstream identities or contracts already provided
- Deliverables and definition of done must be explicit
- Keep the active operating mode visible through `docs/spec-modes/` and `current/`
