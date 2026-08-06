"""Contract tests for AIP-010 Make quality targets and scripts/quality runners.

These tests are read-only: they inspect Makefile/scripts text and dry-run
arch_check. They do not invoke the full lint/type/test suite.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MAKEFILE = REPO_ROOT / "Makefile"
QUALITY_DIR = REPO_ROOT / "scripts" / "quality"

REQUIRED_MAKE_TARGETS = [
    "lint",
    "type-check",
    "arch-check",
    "test-unit",
    "test-integration",
    "test-frontend",
    "build",
    "ci-fast",
    "ci",
    "test",
]

REQUIRED_SCRIPTS = [
    "lib.sh",
    "lint.sh",
    "typecheck.sh",
    "arch_check.py",
    "arch_exceptions.toml",
    "test_unit.sh",
    "test_integration.sh",
    "test_frontend.sh",
    "build.sh",
    "ci_fast.sh",
    "ci.sh",
]


def _makefile_text() -> str:
    return MAKEFILE.read_text(encoding="utf-8")


def test_required_make_targets_exist() -> None:
    text = _makefile_text()
    missing = []
    for target in REQUIRED_MAKE_TARGETS:
        # Match "target:" at line start (allow hyphens).
        if not re.search(rf"^{re.escape(target)}\s*:", text, flags=re.MULTILINE):
            missing.append(target)
    assert not missing, f"Makefile missing targets: {missing}"


def test_make_targets_delegate_to_quality_scripts() -> None:
    text = _makefile_text()
    expected = {
        "lint": "scripts/quality/lint.sh",
        "type-check": "scripts/quality/typecheck.sh",
        "arch-check": "scripts/quality/arch_check.py",
        "test-unit": "scripts/quality/test_unit.sh",
        "test-integration": "scripts/quality/test_integration.sh",
        "test-frontend": "scripts/quality/test_frontend.sh",
        "build": "scripts/quality/build.sh",
        "ci-fast": "scripts/quality/ci_fast.sh",
        "ci": "scripts/quality/ci.sh",
    }
    for target, script in expected.items():
        # Extract recipe block until next target-ish line.
        m = re.search(
            rf"^{re.escape(target)}\s*:.*\n((?:[ \t].*\n|\n)*)",
            text,
            flags=re.MULTILINE,
        )
        assert m, f"could not parse recipe for {target}"
        recipe = m.group(1)
        assert script in recipe, f"{target} recipe must call {script}; got:\n{recipe}"


def test_quality_scripts_exist_and_are_executable() -> None:
    missing = []
    not_exec = []
    for name in REQUIRED_SCRIPTS:
        path = QUALITY_DIR / name
        if not path.is_file():
            missing.append(name)
            continue
        if name.endswith((".sh", ".py")):
            mode = path.stat().st_mode
            if not (mode & stat.S_IXUSR):
                not_exec.append(name)
    assert not missing, f"missing scripts: {missing}"
    assert not not_exec, f"scripts not executable: {not_exec}"


def test_typecheck_script_uses_mypy_config_file() -> None:
    text = (QUALITY_DIR / "typecheck.sh").read_text(encoding="utf-8")
    assert "--config-file backend/pyproject.toml" in text
    assert "mypy backend" in text


def test_lint_script_is_read_only() -> None:
    text = (QUALITY_DIR / "lint.sh").read_text(encoding="utf-8")
    # Must not auto-fix.
    assert "--fix" not in text
    # format must be check-only when present.
    if "ruff format" in text:
        assert "ruff format --check" in text
        # Disallow bare `ruff format backend` without --check.
        for line in text.splitlines():
            if "ruff format" in line and "--check" not in line and not line.strip().startswith("#"):
                pytest.fail(f"lint.sh has non-check format invocation: {line}")


def test_all_shell_gates_are_read_only() -> None:
    offenders: list[str] = []
    for name in REQUIRED_SCRIPTS:
        if not name.endswith(".sh"):
            continue
        text = (QUALITY_DIR / name).read_text(encoding="utf-8")
        if re.search(r"(^|[\s])--fix([\s]|$)", text):
            offenders.append(f"{name}: contains --fix")
        # Disallow `ruff format` without --check.
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "ruff format" in stripped and "--check" not in stripped:
                offenders.append(f"{name}: {stripped}")
    assert not offenders, "read-only violations:\n" + "\n".join(offenders)


def test_arch_check_dry_run_passes() -> None:
    proc = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            "backend",
            "python",
            str(QUALITY_DIR / "arch_check.py"),
        ],
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": "."},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"arch_check failed rc={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "PASS [architecture]" in proc.stdout


def test_arch_exceptions_registry_exists_and_has_entries() -> None:
    path = QUALITY_DIR / "arch_exceptions.toml"
    text = path.read_text(encoding="utf-8")
    assert "[[exceptions]]" in text
    assert "domain-no-sqlalchemy" in text
    assert "AIP-011" in text


def test_test_frontend_script_mentions_issue_075() -> None:
    text = (QUALITY_DIR / "test_frontend.sh").read_text(encoding="utf-8")
    assert "#075" in text or "issue #075" in text


def test_integration_script_blocks_without_false_pass() -> None:
    text = (QUALITY_DIR / "test_integration.sh").read_text(encoding="utf-8")
    assert "BLOCKED" in text or "qg_blocked" in text
    assert "make infra" in text
    assert "exit 2" in text or "exit 2" in text


# ── AIP-010 #076 hosted workflow contracts ──────────────────────────

WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
RUNBOOK_PATH = REPO_ROOT / "docs" / "ci" / "branch-protection-activation.md"

# Stable check names from rules/quality-gates.md Hosted CI Contract.
STABLE_CHECKS: dict[str, tuple[str, str]] = {
    # check title → (workflow file stem, job name)
    "quality / lint-and-type": ("quality", "lint-and-type"),
    "quality / architecture": ("quality", "architecture"),
    "test / backend-unit": ("test", "backend-unit"),
    "test / backend-integration": ("test", "backend-integration"),
    "test / frontend": ("test", "frontend"),
    "build / frontend": ("build", "frontend"),
}


def _load_workflow(stem: str) -> dict:
    path = WORKFLOWS_DIR / f"{stem}.yml"
    assert path.is_file(), f"missing workflow: {path}"
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:  # pragma: no cover - PyYAML may be transitive
        pytest.skip("PyYAML not installed")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"workflow {stem} did not parse to mapping"
    return data


def test_hosted_workflows_exist_with_stable_names() -> None:
    for check, (stem, job_name) in STABLE_CHECKS.items():
        data = _load_workflow(stem)
        assert data.get("name") == stem, (
            f"{check}: workflow name must be {stem!r}, got {data.get('name')!r}"
        )
        jobs = data.get("jobs") or {}
        assert job_name in jobs, f"{check}: missing job key {job_name!r} in {stem}.yml"
        job = jobs[job_name]
        # Job display name defaults to key; if `name:` set it must match.
        display = job.get("name", job_name)
        assert display == job_name, (
            f"{check}: job display name must be {job_name!r}, got {display!r}"
        )


def test_hosted_workflows_pin_python_312_and_lockfiles() -> None:
    quality = _load_workflow("quality")
    test_wf = _load_workflow("test")

    for stem, data in ("quality", quality), ("test", test_wf):
        env = data.get("env") or {}
        assert env.get("PYTHON_VERSION") == "3.12", f"{stem}: PYTHON_VERSION must be 3.12"
        blob = (WORKFLOWS_DIR / f"{stem}.yml").read_text(encoding="utf-8")
        assert "uv sync --project backend --frozen" in blob
        assert "backend/uv.lock" in blob

    build_blob = (WORKFLOWS_DIR / "build.yml").read_text(encoding="utf-8")
    assert "pnpm install --frozen-lockfile" in build_blob
    assert "frontend/pnpm-lock.yaml" in build_blob
    # quality + test also install frontend where needed
    assert "pnpm install --frozen-lockfile" in (WORKFLOWS_DIR / "quality.yml").read_text(
        encoding="utf-8"
    )
    assert "pnpm install --frozen-lockfile" in (WORKFLOWS_DIR / "test.yml").read_text(
        encoding="utf-8"
    )


def test_hosted_workflows_use_synthetic_config_not_production_secrets() -> None:
    for stem in ("quality", "test"):
        blob = (WORKFLOWS_DIR / f"{stem}.yml").read_text(encoding="utf-8")
        assert "ENCRYPTION_KEY:" in blob
        assert "PRIVACY_QUARANTINE_KEY:" in blob
        # Empty provider keys — no live LLM in CI.
        assert "OPENAI_API_KEY:" in blob
        assert "ANTHROPIC_API_KEY:" in blob
        # Must not reference GitHub secrets for encryption keys.
        assert "secrets.ENCRYPTION_KEY" not in blob
        assert "secrets.OPENAI_API_KEY" not in blob


def test_integration_job_declares_postgres_redis_and_preserves_failure() -> None:
    data = _load_workflow("test")
    job = data["jobs"]["backend-integration"]
    services = job.get("services") or {}
    assert "postgres" in services, "integration job must declare postgres service"
    assert "redis" in services, "integration job must declare redis service"
    pg = services["postgres"]
    assert "postgres:16" in str(pg.get("image", ""))
    redis = services["redis"]
    assert "redis:7" in str(redis.get("image", ""))

    blob = (WORKFLOWS_DIR / "test.yml").read_text(encoding="utf-8")
    assert "make test-integration" in blob
    assert "QG_PG_PORT" in blob
    # Failure preservation: upload with if: always() pattern present.
    assert "if: always()" in blob
    assert "gate-backend-integration" in blob
    # Runner bootstrap must create ai_interview_test without host postgresql-client.
    # Service healthchecks may still use in-container pg_isready; job steps must not.
    assert "ai_interview_test" in blob
    assert "asyncpg" in blob
    assert "Create integration test database" in blob

    # Extract only the CREATE-DB step body (between its name: and the next step name:).
    create_idx = blob.index("Create integration test database")
    after = blob[create_idx:]
    # Next top-level step under the same job starts with "      - name:"
    next_step = after.find("\n      - name:", 1)
    create_step = after if next_step < 0 else after[:next_step]
    assert "asyncpg" in create_step
    assert "pg_isready" not in create_step
    assert "psql " not in create_step
    assert "apt-get" not in create_step  # prefer lockfile runtime over apt client


def test_hosted_jobs_call_make_or_shared_quality_commands() -> None:
    """Local/hosted parity: jobs invoke Make targets or the same underlying commands."""
    quality_blob = (WORKFLOWS_DIR / "quality.yml").read_text(encoding="utf-8")
    assert "make lint" in quality_blob
    assert "make type-check" in quality_blob
    assert "make arch-check" in quality_blob

    test_blob = (WORKFLOWS_DIR / "test.yml").read_text(encoding="utf-8")
    assert "make test-integration" in test_blob
    assert "make test-frontend" in test_blob
    assert "pytest backend/tests/unit" in test_blob

    build_blob = (WORKFLOWS_DIR / "build.yml").read_text(encoding="utf-8")
    assert "make build" in build_blob


def test_branch_protection_runbook_separates_merge_from_activation() -> None:
    assert RUNBOOK_PATH.is_file(), f"missing runbook: {RUNBOOK_PATH}"
    text = RUNBOOK_PATH.read_text(encoding="utf-8")
    # Six stable names documented.
    for check in STABLE_CHECKS:
        assert check in text, f"runbook missing stable check name: {check}"
    # Separation of concerns.
    assert "does **not** enable branch" in text or "does not enable branch" in text.lower()
    assert "Rollback" in text or "rollback" in text
    assert "explicit" in text.lower()
    # Must not instruct unattended agents to PUT protection without auth.
    assert "without a human-approved authorization" in text or "Do not activate without" in text
