# RIP-009 Tasks

| Issue | Deliverable | Depends On | Evidence |
| --- | --- | --- | --- |
| #058 | Local redactor, placeholder manifest, residual scanner | - | unit tests |
| #059 | Privacy model/state migration | #058 | migration + model tests |
| #060 | Encrypted quarantine, review API, expiry cleanup | #058, #059 | API/integration tests |
| #061 | Masked pipeline and central LLM guard | #060 | gateway-spy tests |
| #062 | Draft sanitizer and Builder AI boundaries | #059, #061 | service/API tests |
| #063 | Transient hydrated preview/export and photo | #062 | renderer/API tests |
| #064 | Upload privacy review UI | #060, #061 | frontend/browser tests |
| #065 | Export replacement and print UI | #063 | frontend/browser tests |
| #066 | Legacy remediation and acceptance closeout | #061-#065 | dry-run, E2E, docs |

