# RIP-007 Tasks

**Feature**: JD 列表与智能识别
**Status**: Planned
**PRD**: `tasks/prd-jd-library.md`
**SPEC**: `specs/RIP-007-jd-library/spec.md`
**Depends on**: RIP-003 JD Matching

## Issue List

- [ ] [issue-039: JD library schema and domain contracts](../../tasks/issues/issue-039-rip007-jd-library-schema.md)
- [ ] [issue-040: Text and file JD import service](../../tasks/issues/issue-040-rip007-jd-text-file-import.md)
- [ ] [issue-041: Secure public URL JD extraction](../../tasks/issues/issue-041-rip007-secure-url-import.md)
- [ ] [issue-042: Celery JD processing and duplicate state machine](../../tasks/issues/issue-042-rip007-jd-processing-pipeline.md)
- [ ] [issue-043: JD list, detail and edit APIs](../../tasks/issues/issue-043-rip007-jd-list-detail-edit-api.md)
- [ ] [issue-044: JD retry, re-extract, duplicate and protected delete APIs](../../tasks/issues/issue-044-rip007-jd-state-command-api.md)
- [ ] [issue-045: JD navigation, list and three-mode import UI](../../tasks/issues/issue-045-rip007-jd-list-import-ui.md)
- [ ] [issue-046: JD detail editor and recovery UI](../../tasks/issues/issue-046-rip007-jd-detail-ui.md)
- [ ] [issue-047: JD library integration and security acceptance](../../tasks/issues/issue-047-rip007-jd-library-acceptance.md)

## Dependency Order

```text
039
├── 040 ─┐
└── 041 ─┴→ 042 → 043 → 044 → 045 → 046 → 047
```

