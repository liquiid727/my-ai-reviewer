# [RIP-009] Legacy remediation and privacy acceptance

Inventory and purge historic cleartext artifacts, re-mask recoverable resources, and close the feature with end-to-end evidence.

## Acceptance Criteria
- [ ] Dry-run reports counts without writes or values
- [ ] Execute removes source, photo, PDF, and unsafe AI history artifacts
- [ ] Repeated execution is idempotent
- [ ] Full backend/frontend/security acceptance suite passes

**Type:** fullstack  
**Priority:** high  
**Depends on:** #061, #062, #063, #064, #065  
**SPEC:** `specs/RIP-009-resume-privacy/spec.md`

