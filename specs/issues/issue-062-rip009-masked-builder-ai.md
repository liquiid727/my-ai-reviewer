# [RIP-009] Masked Builder persistence and AI boundaries

Sanitize all draft writes, keep draft manifests safe, and prevent Builder AI from receiving or writing clear identity data.

## Acceptance Criteria
- [ ] Profile-to-draft and direct edits persist masked content
- [ ] Titles and local history do not retain names or filenames
- [ ] Assistant/polish/score are privacy guarded
- [ ] Identity replacement operations cannot introduce cleartext

**Type:** fullstack  
**Priority:** high  
**Depends on:** #059, #061  
**SPEC:** `specs/RIP-009-resume-privacy/spec.md`

