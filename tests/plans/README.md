# Test Plans

This directory stores normalized `test-plan` artifacts derived from feature specs.

Each plan should define:

- `spec_id`
- `spec_version`
- feature name
- design/roadmap/spec source
- business `flows` with ordered `stages`
- endpoint list with branch coverage, preconditions, expected results, and related rule
- scenario list with steps, branches, preconditions, and expected results

`test-plan` is the semantic bridge between feature specs and concrete execution assets such as Bruno collections or scenario scripts.
