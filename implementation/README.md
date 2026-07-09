# Implementation

Implementation handoff and status artifacts live here.

If the project is running `LiteSpec`, some implementation notes may stay close to the feature directory.

If the project is running `EnterpriseSpec`, use this directory for explicit implementation, rollout, and rollback evidence.

Recommended shape:

```text
implementation/
  _template/
    implementation-note.template.md
  RP-002-decision-api/
    implementation-notes.md
```

Use one directory per `spec_id` when implementation notes or handoff artifacts need to be stored outside the code diff itself.
