# Issues

Index of feature bundles and local issues produced by `/to-issues`.

Each local issue should stay small enough for a single `/goal` run to finish end to end, with explicit acceptance criteria and evidence.

| Feature | Spec Directory | Status | Depends on |
| --- | --- | --- | --- |
| RIP-001 | specs/RIP-001-resume-multiformat-parsers | in-review | — |
| RIP-002 | specs/RIP-002-resume-fact-profile-persistence | shipped | RIP-001 |
| RIP-003 | specs/RIP-003-jd-matching | shipped | RIP-002 |
| RIP-005 | specs/RIP-005-resume-auto-pagination | in-progress | RIP-004 |
| RIP-009 | specs/RIP-009-resume-privacy | open | RIP-001, RIP-002, RIP-004, RIP-006 |
| RIP-010 | specs/RIP-010-job-target-input-versions | proposed | RIP-002, RIP-007, RIP-009 |
| RIP-010 | specs/RIP-010-jd-vision-import | proposed | RIP-007 |
| RIP-011 | specs/RIP-011-jd-review-version-publishing | proposed | RIP-007, RIP-010 |
| RIP-011 | specs/RIP-011-evidence-bound-jd-matching | proposed | RIP-002, RIP-003, RIP-009, RIP-010 |
| RIP-012 | specs/RIP-012-jd-source-expansion | proposed | RIP-001, RIP-011 |
| RIP-012 | specs/RIP-012-jd-matching-consumption | proposed | RIP-008, RIP-011 |
| RIP-013 | specs/RIP-013-match-assessment-engine | proposed | RIP-003, RIP-010, RIP-012 |
| RIP-014 | specs/RIP-014-match-report-plan-bridge | proposed | RIP-008, RIP-013 |
| AIP-009 | specs/AIP-009-quality-governance-foundation | proposed | — |
| AIP-010 | specs/AIP-010-ci-test-quality-gates | proposed | AIP-009 |
| AIP-011 | specs/AIP-011-architecture-modularization | proposed | AIP-009, AIP-010 |
| AIP-012 | specs/AIP-012-error-observability | proposed | AIP-009, AIP-010 |
| AIP-013 | specs/AIP-013-interview-scenario-registry | proposed | AIP-001 |
| AIP-014 | specs/AIP-014-interview-plan-approval | proposed | AIP-013, RIP-013, RIP-014 |
| AIP-015 | specs/AIP-015-interview-session-state-events | proposed | AIP-001, AIP-014, RIP-009 |
| AIP-016 | specs/AIP-016-coverage-interview-runtime | proposed | AIP-013, AIP-015, RIP-009 |
| AIP-017 | specs/AIP-017-interview-report-history-actions | proposed | AIP-016, RIP-008, RIP-014 |

Current incremental issue: `#038` (TXT/Markdown encoding fallback) is implemented locally and waiting for review / release.

## JD Intelligence v2 Issue Drafts

These are local proposed issues generated from `spec-draft/jd-intelligence-v2-2026-08-05.md`. Issue #092 establishes the factual baseline; code presence in older RIPs is not treated as acceptance evidence.

| Issue | Spec ID | Status | Depends on |
| --- | --- | --- | --- |
| #092 | RIP-010/RIP-011/RIP-012 | proposed | — |
| #093 | RIP-010 | proposed | #092 |
| #094 | RIP-010 | proposed | #092, #093 |
| #095 | RIP-010 | proposed | #094 |
| #096 | RIP-010 | proposed | #095 |
| #097 | RIP-010 | proposed | #096 |
| #098 | RIP-011 | proposed | #092, #097 |
| #099 | RIP-011 | proposed | #098 |
| #100 | RIP-011 | proposed | #093, #098, #099 |
| #101 | RIP-011 | proposed | #100 |
| #102 | RIP-011 | proposed | #101 |
| #103 | RIP-012 | proposed | #102 |
| #104 | RIP-012 | proposed | #101, RIP-008 |
| #105 | RIP-012 | proposed | #101, RIP-009 |
| #106 | RIP-012 | proposed | #097, #102, #103, #104, #105 |

Status transitions map to the six-step loop:

1. `/prd` -> spec-draft accepted
2. `/prd-to-spec` (optional) -> design updated
3. `/to-issues` -> issue added to this table as `open`
4. `/goal` -> issue moves to `in-progress`, then to `in-review`
5. `/review-it` -> issue stays `in-review` until findings are resolved
6. `/ship-it` -> issue moves to `shipped` and is closed

## Engineering Quality Governance Issue Drafts

These are local proposed issues. They are not GitHub issues and do not change the active RIP-001/RIP-009 delivery state.

| Issue | Spec ID | Status | Depends on |
| --- | --- | --- | --- |
| #067 | AIP-009 | proposed | — |
| #068 | AIP-009 | proposed | #067 |
| #069 | AIP-009 | proposed | #067, #068 |
| #070 | AIP-010 | proposed | #069 |
| #071 | AIP-010 | proposed | #070 |
| #072 | AIP-010 | proposed | #071 |
| #073 | AIP-010 | proposed | #070 |
| #074 | AIP-010 | proposed | #071, #072, #073 |
| #075 | AIP-010 | proposed | #069 |
| #076 | AIP-010 | proposed | #074, #075 |
| #077 | AIP-011 | proposed | #074 |
| #078 | AIP-011 | proposed | #077 |
| #079 | AIP-011 | proposed | #077 |
| #080 | AIP-011 | proposed | #077 |
| #081 | AIP-011 | proposed | #077 |
| #082 | AIP-011 | proposed | #081 |
| #083 | AIP-011 | proposed | #078, #079, #080, #082 |
| #084 | AIP-011 | proposed | #075, #081 |
| #085 | AIP-012 | proposed | #074 |
| #086 | AIP-012 | proposed | #078, #085 |
| #087 | AIP-012 | proposed | #079, #080, #085 |
| #088 | AIP-012 | proposed | #081, #084, #085 |
| #089 | AIP-012 | proposed | #085 |
| #090 | AIP-012 | proposed | #089 |
| #091 | AIP-012 | proposed | #086, #087, #088, #089, #090 |

## Job Target Interview Program Issue Drafts

These are local proposed issues from the Job Target Interview Training Program. They are not GitHub issues and do not change active delivery state.

| Issue | Spec ID | Status | Depends on |
| --- | --- | --- | --- |
| #92 | RIP-010 | proposed | issue #038 delivery gate |
| #93 | RIP-010 | proposed | #092 |
| #94 | RIP-010 | proposed | #092 |
| #95 | RIP-010 | proposed | #093, #094 |
| #96 | RIP-010 | proposed | #095 |
| #97 | RIP-011 | proposed | #094 |
| #98 | RIP-011 | proposed | #097 |
| #99 | RIP-011 | proposed | #092, #098 |
| #100 | RIP-011 | proposed | #099 |
| #101 | RIP-011 | proposed | #098, #099, #100 |
| #102 | RIP-011 | proposed | #101 |
| #103 | RIP-012 | proposed | issue #030, #102 |
| #104 | RIP-012 | proposed | #102 |
| #105 | RIP-012 | proposed | #103, #104 |
| #106 | RIP-012 | proposed | #105 |
| #107 | RIP-013 | proposed | #106 |
| #108 | RIP-013 | proposed | #107 |
| #109 | RIP-013 | proposed | #092, #093, #107 |
| #110 | RIP-013 | proposed | #108, #109 |
| #111 | RIP-013 | proposed | #110 |
| #112 | RIP-014 | proposed | issue #057, #111 |
| #113 | RIP-014 | proposed | #110, #112 |
| #114 | RIP-014 | proposed | #096, #113 |
| #115 | RIP-014 | proposed | #111, #114 |
| #116 | AIP-013 | proposed | issue #038 delivery gate |
| #117 | AIP-014 | proposed | #111, #116 |
| #118 | AIP-014 | proposed | #107, #117 |
| #119 | AIP-014 | proposed | #118 |
| #120 | AIP-014 | proposed | #114, #116, #119 |
| #121 | AIP-014 | proposed | #120 |
| #122 | AIP-015 | proposed | #121 |
| #123 | AIP-015 | proposed | #122 |
| #124 | AIP-015 | proposed | #119, #122, #123 |
| #125 | AIP-015 | proposed | #116, #124 |
| #126 | AIP-015 | proposed | #123, #125 |
| #127 | AIP-015 | proposed | #124, #126 |
| #128 | AIP-015 | proposed | #125, #127 |
| #129 | AIP-016 | proposed | #116, #123 |
| #130 | AIP-016 | proposed | #118, #124, #129 |
| #131 | AIP-016 | proposed | #122, #130 |
| #132 | AIP-016 | proposed | #125, #131 |
| #133 | AIP-016 | proposed | #127, #132 |
| #134 | AIP-016 | proposed | #128, #133 |
| #135 | AIP-017 | proposed | #132, #134 |
| #136 | AIP-017 | proposed | #135 |
| #137 | AIP-017 | proposed | #112, #136 |
| #138 | AIP-017 | proposed | #123, #136, #137 |
| #139 | AIP-017 | proposed | #138 |
| #140 | AIP-017 | proposed | #137, #139 |
