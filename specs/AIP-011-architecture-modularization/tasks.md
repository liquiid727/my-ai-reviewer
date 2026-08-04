# AIP-011 Tasks

| Issue | Deliverable | Depends On | Evidence |
|---|---|---|---|
| #077 | Harden dependency checker and add exception registry | AIP-010/#074 | architecture gate tests |
| #078 | Resume application use cases and ports | #077 | characterization + import checks |
| #079 | JD application use cases and ports | #077 | JD unit/API + import checks |
| #080 | Plan application use cases and ports | #077 | Plan unit/API + import checks |
| #081 | Builder route side-effect extraction | #077 | API/privacy contract tests |
| #082 | Builder service decomposition | #081 | domain/application unit tests |
| #083 | ORM models split by aggregate | #078, #079, #080, #082 | metadata/migration smoke |
| #084 | Builder frontend feature split and shared client/polling | AIP-010/#075, #081 | component/browser/build evidence |
