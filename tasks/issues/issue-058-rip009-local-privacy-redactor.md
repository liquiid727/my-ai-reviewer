# [RIP-009] Local privacy redactor and safe manifest

Implement typed recognizers, deterministic placeholders, overlap resolution, residual scanning, and a manifest that never contains original values.

## Acceptance Criteria
- [ ] Chinese and English privacy fixtures are fully masked
- [ ] Repeated entities share stable tokens
- [ ] Manifest and logs contain no original values
- [ ] Missing local model fails closed

**Type:** backend  
**Priority:** high  
**Depends on:** None  
**SPEC:** `specs/RIP-009-resume-privacy/spec.md`

