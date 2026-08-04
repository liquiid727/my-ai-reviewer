# Branch Protection Activation Runbook (AIP-010 / #076)

This runbook separates **workflow merge** from **required-check activation**.
Merging `.github/workflows/{quality,test,build}.yml` does **not** enable branch
protection. Activation is an external repository-admin action that requires
explicit ship/repository authorization.

## 1. Stable check names

Source of truth: `rules/quality-gates.md` → Hosted CI Contract.

| Required check name | Workflow file | Job `name` | Local equivalent |
|---|---|---|---|
| `quality / lint-and-type` | `.github/workflows/quality.yml` | `lint-and-type` | `make lint` + `make type-check` |
| `quality / architecture` | `.github/workflows/quality.yml` | `architecture` | `make arch-check` |
| `test / backend-unit` | `.github/workflows/test.yml` | `backend-unit` | backend portion of `make test-unit` |
| `test / backend-integration` | `.github/workflows/test.yml` | `backend-integration` | `make test-integration` |
| `test / frontend` | `.github/workflows/test.yml` | `frontend` | `make test-frontend` |
| `build / frontend` | `.github/workflows/build.yml` | `frontend` | `make build` |

GitHub formats check titles as `<workflow name> / <job name>`. The three
workflow `name:` fields (`quality`, `test`, `build`) are chosen so the six
titles match the table above exactly.

## 2. Preconditions before activation

1. Workflows are merged to the default branch (`main`).
2. At least one successful run of each job exists on `main` (GitHub only lists
   checks that have produced a status). Confirm in the Actions tab:
   - `quality / lint-and-type`
   - `quality / architecture`
   - `test / backend-unit`
   - `test / backend-integration`
   - `test / frontend`
   - `build / frontend`
3. Local parity still green from repo root:
   ```bash
   make ci-fast
   make test-integration   # requires make infra (Postgres :5433, Redis :6379)
   make test-frontend
   ```
4. Explicit authorization recorded (issue comment, ship approval, or admin
   change ticket). **Do not activate without it.**

## 3. Activation steps (repository admin)

UI path (GitHub.com):

1. Settings → Branches → Branch protection rules → rule for `main`
   (create if missing).
2. Enable **Require status checks to pass before merging**.
3. Enable **Require branches to be up to date before merging** (recommended).
4. Add exactly these six status checks (names must match character-for-character):
   - `quality / lint-and-type`
   - `quality / architecture`
   - `test / backend-unit`
   - `test / backend-integration`
   - `test / frontend`
   - `build / frontend`
5. Leave **Do not require required reviews from Code Owners** / admin bypass
   policy as decided by the repo owner. Prefer **not** allowing administrators
   to bypass required checks in normal operation.
6. Save changes.
7. Record activation evidence:
   - date (UTC)
   - actor
   - rule screenshot or `gh api` dump of the protection rule
   - link to authorizing issue/comment

CLI alternative (requires `admin:repo_hook` / administration scope):

```bash
# INSPECT current rule (safe, read-only)
gh api repos/{owner}/{repo}/branches/main/protection

# APPLY only after explicit authorization. Example payload — review before use.
# gh api -X PUT repos/{owner}/{repo}/branches/main/protection \
#   --input branch-protection-payload.json
```

Do **not** paste live tokens into the payload file. Do **not** run the PUT
from an unattended agent loop without a human-approved authorization record.

## 4. What activation does *not* include

- Production deploy keys, environments, or release automation.
- Mutating repository secrets to real LLM/provider credentials for CI.
  Workflows use synthetic Fernet keys and empty provider API keys only.
- Changing Make target semantics or relaxing gates with `--fix`.
- Closing AIP-010 or marking coverage thresholds enforced beyond measure-only
  baseline policy in `rules/quality-gates.md`.

## 5. Rollback

If required checks block legitimate delivery or a workflow is broken on `main`:

### 5.1 Fast rollback (un-require checks)

1. Settings → Branches → `main` protection → remove the failing check(s) from
   the required list, **or** temporarily disable “Require status checks”.
2. Record rollback reason, actor, UTC timestamp, and the checks removed.
3. Open a follow-up issue to restore protection after the workflow fix merges.

### 5.2 Workflow fix forward

1. Fix the shared script (`scripts/quality/*`) and/or workflow YAML on a branch.
2. Verify locally with the matching Make target.
3. Merge the fix; confirm the six checks go green on `main`.
4. Re-add any checks removed in 5.1.

### 5.3 Disable a workflow entirely (last resort)

```bash
gh workflow disable quality.yml
gh workflow disable test.yml
gh workflow disable build.yml
```

Re-enable with `gh workflow enable <file>` after repair. Disabling does not
remove branch-protection entries — clear required checks first or merges stay
blocked on missing statuses.

## 6. Local ↔ hosted parity notes

| Concern | Local | Hosted |
|---|---|---|
| Entry point | `make <target>` → `scripts/quality/*.sh` | job step → same `make <target>` / equivalent script command |
| Python | 3.12+ via uv project | pinned `PYTHON_VERSION=3.12`, `uv sync --frozen` |
| Node / pnpm | developer toolchain | `NODE_VERSION=22`, `PNPM_VERSION=10.11.0`, `pnpm install --frozen-lockfile` |
| Postgres | `localhost:5433` (compose) | service container `localhost:5432`; `QG_PG_PORT=5432`; test DB `ai_interview_test` created via in-process `asyncpg` (no host `psql`) |
| Redis | `localhost:6379` | service container `localhost:6379` |
| Secrets | developer `.env` | synthetic keys in workflow `env:` only |
| Failure preservation | script exit codes 1 (FAIL) / 2 (BLOCKED) | job uploads artifacts with `if: always()` then fails |

## 7. Evidence and safety

- Artifacts upload junit/logs/result markers only. Do **not** upload resume
  fixtures, `.env`, quarantine objects, or provider transcripts.
- CI configuration must stay synthetic (empty `OPENAI_API_KEY` /
  `ANTHROPIC_API_KEY`, deterministic Fernet test keys).
- Normalized gate evidence for delivery reviews still lives under
  `tests/results/` per `tests/_template/quality-gate-result.template.json`.

## 8. Authorization checklist (copy into the activating issue)

```text
[ ] Workflows merged to main and observed green once
[ ] Six check titles verified in Actions UI
[ ] make ci-fast + integration + frontend green locally
[ ] Explicit activation authorization recorded (who/when/where)
[ ] Branch protection updated with the six required checks
[ ] Activation evidence attached (screenshot or API dump)
[ ] Rollback owner named
```
