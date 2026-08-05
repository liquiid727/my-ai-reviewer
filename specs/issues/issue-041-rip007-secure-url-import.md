# [RIP-007] Secure public URL JD extraction

## Description

Fetch public job pages without exposing internal networks, then extract bounded visible body text for the JD pipeline.

## Acceptance Criteria
- [ ] Add `SafeWebFetcher` using `httpx` with environment proxies disabled
- [ ] Reject credentials, unsupported schemes, disallowed ports and every non-global A/AAAA result
- [ ] Manually validate at most three redirects, including DNS checks on every hop
- [ ] Enforce connect/read/total timeouts, 2MB streamed response limit and HTML/plain-text MIME allowlist
- [ ] Use `trafilatura` for primary正文 extraction and the exposed in-memory HTML visible-text fallback once
- [ ] Never execute JavaScript or attempt login/captcha/anti-bot bypass
- [ ] Add `/jd/import/url` through `JDImportService`
- [ ] Unit tests cover private/loopback/link-local/reserved IPv4 and IPv6, redirects, rebinding guard inputs, timeout, MIME and body limit

## Dependencies

- `tasks/issues/issue-039-rip007-jd-library-schema.md`

## Type

backend / security

## Priority

high

## PRD Reference

`tasks/prd-jd-library.md` - US-002; FR-4, FR-5, FR-6

## SPEC Reference

`specs/RIP-007-jd-library/spec.md` - RIP-007 Sections 2.3, 5.4, 7.2

