# [RIP-009] Encrypted quarantine and review API

Store uploads in one-hour encrypted quarantine, perform local scanning, expose no-store masked review, and delete every approved/expired/failed source.

## Acceptance Criteria
- [ ] Quarantine ciphertext cannot be parsed as the source file
- [ ] Auto and review-required branches are supported
- [ ] Manual spans use optimistic revision control
- [ ] Approval and expiry delete source objects

**Type:** backend  
**Priority:** high  
**Depends on:** #058, #059  
**SPEC:** `specs/RIP-009-resume-privacy/spec.md`

