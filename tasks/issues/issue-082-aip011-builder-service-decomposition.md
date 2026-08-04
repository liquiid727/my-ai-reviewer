# [AIP-011] Decompose Builder services by use case

Split Builder creation/edit/proposal/polish/score/render policies into cohesive domain/application units.

## Acceptance Criteria
- [ ] Each extracted unit has one named responsibility and narrow typed dependencies
- [ ] Domain code imports no ORM, storage, renderer, evaluator, polisher, or LLM implementation
- [ ] No generic facade/repository is introduced without multiple concrete consumers
- [ ] Characterization, revision, privacy, rendering, and service unit tests pass

- **Type:** backend
- **Priority:** medium
- **Depends on:** #081
- **SPEC:** `specs/AIP-011-architecture-modularization/spec.md` (Sections 5-8)
