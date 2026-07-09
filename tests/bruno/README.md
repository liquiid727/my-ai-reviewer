# Bruno

HTTP collection and scenario assets generated from feature specs and API contracts belong here.

Bruno outputs should be treated as execution assets. The independent test console should read normalized files from `tests/results/` instead of parsing Bruno-native output directly.

Generate a collection from a normalized test plan:

```bash
node packages/cli/dist/main.js generate-bruno-tests <specId>
```

Generated files live under `tests/bruno/<specId>/` and include `bruno.json`, one `.bru` request per endpoint, and a collection README.

## Runner Contract

`specos run-api-tests <specId>` expects API execution assets under:

```text
tests/bruno/<specId>/
```

When assets or execution adapter configuration are missing, the runner writes a blocked normalized result instead of reporting success.

Bind a real Bruno command with:

```bash
node packages/cli/dist/main.js run-api-tests <specId> --command "bru run tests/bruno/<specId>"
```

The command is executed from the project root. Exit code `0` is normalized as pass/ready; any other exit code is normalized as warning/blocked.
