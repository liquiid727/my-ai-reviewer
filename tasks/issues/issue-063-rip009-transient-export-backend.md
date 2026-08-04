# [RIP-009] Transient hydrated preview and export backend

Apply exact placeholder replacements to an in-memory draft copy and process an optional photo without persistence.

## Acceptance Criteria
- [ ] Partial replacement safely leaves missing tokens masked
- [ ] Unknown tokens are rejected without echoing values
- [ ] Photo and hydrated PDF create no MinIO/DB records
- [ ] Preview/export are no-store and share renderer behavior

**Type:** backend  
**Priority:** high  
**Depends on:** #062  
**SPEC:** `specs/RIP-009-resume-privacy/spec.md`

