# RIP-005 Tests

## Manual acceptance

1. Open `/resumes` and confirm `简历样式模板` appears after `参考模板`.
2. Activate it and confirm the URL is `/resumes/style-templates`.
3. Confirm the page shows `暂无简历样式模板` and does not request template data.
4. Switch to English and confirm the entry and empty state are translated.
5. Return to `/resumes` and confirm the existing upload, draft, and reference-template tabs still render.

## Automated gate

- [x] `pnpm build`
- [x] `pnpm lint`

The browser-based manual checks remain environment-blocked by local URL permission in the current browser session.
