# RIP-005 Tasks

- [x] T1 - Replace `auto_one_page` with `LayoutPolicy` in domain, database, API, and frontend.
- [x] T2 - Add deterministic candidate selection and true PDF page counting.
- [x] T3 - Make preview return the same paginated PDF used for export.
- [x] T4 - Add automatic/target page controls and target-unmet feedback.
- [ ] T5 - Verify templates, tests, frontend build/lint, and browser behavior.

T5 evidence: backend unit tests, frontend build/lint, live API generation, and
rendered PDF visual QA pass. Browser UI control was denied by the browser
permission layer and remains the only open verification path.
