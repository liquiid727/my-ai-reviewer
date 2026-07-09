# Test Plan Schema

Normalized `test-plan` artifacts should be generated from feature specs before selecting execution tools.

Required fields:

- `standardVersion` (`specos-test-standard/v1`) for production plans
- `qualityProfile`
- `riskTier`
- `specId`
- `specVersion`
- `featureName`
- `source`
- `flows[]`
- `endpoints[]`
- `scenarios[]`
- `standardRequirements[]` for production plans
- `flakePolicy` for production plans
- `dataPolicy` for production plans
- `securityPolicy` for production plans

Flow entries should define:

- flow name
- ordered `stages[]`

Each stage should define:

- stage name
- `scenarioNames[]`
- `stepNames[]`

Endpoint entries should define:

- interface name
- method and path
- priority
- branch list
- preconditions
- expected results
- related rule

Scenario entries should define:

- scenario name
- priority
- branch list
- preconditions
- expected results
- ordered steps

Production standard requirement entries should define:

- requirement id
- test layer
- target names in `appliesTo[]`
- risk tiers in `requiredFor[]`
- owner agent
- required evidence types
- gate impact

## Spec To Test Inference

When a spec does not explicitly enumerate all tests, `test-editor` must derive a minimum matrix from the feature spec:

- `api[]` implies API contract, auth/error-code, idempotency, compatibility, and security requirements.
- `userFlows[]` or scenario flows imply scenario/E2E requirements with happy, error, edge, and limit branches.
- `rules[]` implies unit/API/scenario assertion candidates depending on where the rule is enforced.
- `edgeCases[]` implies error and limit branch tests.
- `observability[]` implies trace, log, or metric evidence requirements.
- `performanceTargets[]` and `concurrencyInvariants[]` directly enter performance and concurrency gates.

For a P0 backend/API change with no explicit test fields, the default minimum is unit + API/contract + scenario/E2E + trace evidence. Performance, concurrency, security, migration, compatibility, observability, accessibility, and visual regression become required when the quality profile or spec content declares the corresponding risk.
