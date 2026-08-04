# AIP-009 Test Contract

| Requirement | Verification | Expected result |
|---|---|---|
| One source hierarchy | cross-link and conflict review | rules/design/knowledge/prompt precedence is unambiguous |
| Gate vocabulary | search all AIP-009 artifacts | only defined execution/decision states are used |
| Planned target safety | inspect Makefile and QA instructions | unavailable Make targets are never presented as active |
| Evidence format | parse the JSON template | valid JSON with refs, commands, statuses, exit code, decision, evidence |
| QA least privilege | role/prompt review | no implicit business-code, threshold, test, Git, or ship authorization |
| Privacy | synthetic canary review | templates/prompts require redacted evidence and contain no real PII |
