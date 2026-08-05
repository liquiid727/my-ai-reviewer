# [RIP-010] Add immutable input-version schema and JD v1 backfill

Create the append-only JD/Resume Version persistence foundation and safely backfill every existing ready JD as version 1.

## Acceptance Criteria

- [ ] Add `job_description_versions` and `resume_versions` with exact source/content/version/privacy constraints from RIP-010.
- [ ] Add indexed foreign keys, source-specific partial uniqueness, score-free immutable snapshot fields, and no update/delete command path.
- [ ] Add `job_descriptions.current_version_id` after the version table exists.
- [ ] Backfill ready JDs as v1 without inventing unavailable evidence or changing mutable source rows.
- [ ] Migration upgrade/downgrade and representative legacy-data tests pass from the actual Alembic head.
- [ ] Update `design/database.md` with as-implemented columns, indexes, compatibility, and rollback notes.

- **Type:** backend / database
- **Priority:** high
- **Depends on:** issue #038 delivery gate
- **SPEC:** RIP-010 sections 6.1/6.2, 10, 11
