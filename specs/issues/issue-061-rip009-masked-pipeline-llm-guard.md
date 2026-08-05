# [RIP-009] Masked resume pipeline and LLM guard

Persist only approved masked text and require the privacy guard for all resume-derived model calls.

## Acceptance Criteria
- [ ] Parsing/facts/profile/evidence contain placeholders only
- [ ] Unapproved or residual payloads never call an LLM
- [ ] LLM outputs are scanned before persistence
- [ ] Reparse works from masked content without an original file

**Type:** backend  
**Priority:** high  
**Depends on:** #060  
**SPEC:** `specs/RIP-009-resume-privacy/spec.md`

