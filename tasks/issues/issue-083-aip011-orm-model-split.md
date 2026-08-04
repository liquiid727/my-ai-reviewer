# [AIP-011] Split ORM models by aggregate

Replace the monolithic ORM model file with aggregate modules while preserving one complete SQLAlchemy/Alembic metadata graph.

## Acceptance Criteria
- [ ] Models are grouped by stable aggregate/context with compatibility imports during migration
- [ ] Tables, columns, constraints, indexes, relationships, and mapper order remain compatible
- [ ] Alembic sees all models and produces no unexpected schema diff
- [ ] Model/import/integration tests and migration smoke pass; compatibility removal is tracked

- **Type:** backend
- **Priority:** medium
- **Depends on:** #078, #079, #080, #082
- **SPEC:** `specs/AIP-011-architecture-modularization/spec.md` (Sections 8, 10-11)
