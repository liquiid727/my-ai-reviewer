"""Unit tests for AIP-011 hardened architecture checker.

Covers: clean paths, new-file violations, local/nested imports,
exception registry validation (wildcard/expired/missing fields),
and violation report shape (rule, importer, imported, line).
"""

from __future__ import annotations

import stat
import textwrap
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
ARCH_CHECK = REPO_ROOT / "scripts" / "quality" / "arch_check.py"
ARCH_EXCEPTIONS = REPO_ROOT / "scripts" / "quality" / "arch_exceptions.toml"


@pytest.fixture(scope="module")
def arch_mod():
    """Load arch_check.py as a module without executing main()."""
    import importlib.util
    import sys

    name = "arch_check_under_test"
    spec = importlib.util.spec_from_file_location(name, ARCH_CHECK)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # dataclasses + from __future__ import annotations needs the module in
    # sys.modules before exec_module on Python 3.13+.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def _mini_repo(tmp_path: Path) -> Path:
    """Scaffold a tiny monorepo layout for isolated checker runs."""
    root = tmp_path / "repo"
    for d in (
        "backend/domain/clean",
        "backend/api/v1",
        "backend/application",
        "backend/tasks",
        "backend/infrastructure/db",
        "frontend/src/pages",
        "scripts/quality",
    ):
        (root / d).mkdir(parents=True, exist_ok=True)
    # empty inits so packages exist
    for p in (
        "backend/__init__.py",
        "backend/domain/__init__.py",
        "backend/domain/clean/__init__.py",
        "backend/api/__init__.py",
        "backend/api/v1/__init__.py",
        "backend/application/__init__.py",
        "backend/tasks/__init__.py",
    ):
        (root / p).write_text("", encoding="utf-8")
    return root


def test_arch_check_script_is_executable() -> None:
    assert ARCH_CHECK.is_file()
    mode = ARCH_CHECK.stat().st_mode
    assert mode & stat.S_IXUSR, "arch_check.py must be executable"


def test_repo_arch_check_passes_with_registry(arch_mod) -> None:
    rc, out, err = arch_mod.run_check(root=REPO_ROOT)
    assert rc == 0, "stderr:\n" + "\n".join(err) + "\nstdout:\n" + "\n".join(out)
    assert any("PASS [architecture]" in line for line in out)
    # Hardened scanner covers all layers.
    joined = "\n".join(out)
    assert "domain+api+application+tasks+frontend-pages" in joined


def test_clean_domain_file_passes(arch_mod, tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    _write(
        root / "backend/domain/clean/policy.py",
        """
        from backend.domain.clean import other  # type: ignore
        VALUE = 1
        """,
    )
    _write(root / "scripts/quality/arch_exceptions.toml", "# empty\n")
    rc, out, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 0, err
    assert any("PASS [architecture]" in line for line in out)


def test_new_domain_infrastructure_import_fails(arch_mod, tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    _write(
        root / "backend/domain/clean/leaky.py",
        """
        from backend.infrastructure.db.models import ResumeModel
        """,
    )
    _write(root / "scripts/quality/arch_exceptions.toml", "# empty\n")
    rc, out, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 1
    joined = "\n".join(err)
    assert "domain-no-infrastructure" in joined
    assert "backend/domain/clean/leaky.py" in joined
    assert "backend.infrastructure.db.models" in joined
    # Report shape: rule=, importer=, imported=
    assert "rule=domain-no-infrastructure" in joined
    assert "importer=backend/domain/clean/leaky.py:" in joined
    assert "imported=backend.infrastructure.db.models" in joined


def test_local_import_inside_function_is_detected(arch_mod, tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    _write(
        root / "backend/domain/clean/local_import.py",
        """
        def do_work():
            import sqlalchemy
            from backend.infrastructure.storage.minio_client import download_file
            return sqlalchemy, download_file
        """,
    )
    _write(root / "scripts/quality/arch_exceptions.toml", "# empty\n")
    rc, _, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 1
    joined = "\n".join(err)
    assert "domain-no-sqlalchemy" in joined
    assert "domain-no-infrastructure" in joined
    assert "local_import.py" in joined


def test_exception_waives_exact_path_and_rule(arch_mod, tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    target = "backend/domain/clean/waived.py"
    _write(
        root / target,
        """
        import sqlalchemy
        """,
    )
    expiry = (date.today() + timedelta(days=30)).isoformat()
    _write(
        root / "scripts/quality/arch_exceptions.toml",
        f"""
        [[exceptions]]
        path = "{target}"
        rule = "domain-no-sqlalchemy"
        owner = "AIP-011"
        expiry = "{expiry}"
        reason = "test waiver"
        removal_issue = "#077"
        """,
    )
    rc, out, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 0, err
    assert any("waived" in line for line in out)


def test_wildcard_exception_rejected(arch_mod, tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    expiry = (date.today() + timedelta(days=30)).isoformat()
    _write(
        root / "scripts/quality/arch_exceptions.toml",
        f"""
        [[exceptions]]
        path = "backend/domain/**"
        rule = "domain-no-sqlalchemy"
        owner = "AIP-011"
        expiry = "{expiry}"
        reason = "too broad"
        removal_issue = "#077"
        """,
    )
    rc, _, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 1
    assert any("wildcard" in line.lower() or "directory-wide" in line for line in err)


def test_directory_path_exception_rejected(arch_mod, tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    expiry = (date.today() + timedelta(days=30)).isoformat()
    _write(
        root / "scripts/quality/arch_exceptions.toml",
        f"""
        [[exceptions]]
        path = "backend/domain/"
        rule = "domain-no-sqlalchemy"
        owner = "AIP-011"
        expiry = "{expiry}"
        reason = "directory"
        removal_issue = "#077"
        """,
    )
    rc, _, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 1
    joined = "\n".join(err).lower()
    assert "wildcard" in joined or "directory" in joined or "exact source file" in joined


def test_expired_exception_fails(arch_mod, tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    target = "backend/domain/clean/old.py"
    _write(root / target, "import sqlalchemy\n")
    _write(
        root / "scripts/quality/arch_exceptions.toml",
        f"""
        [[exceptions]]
        path = "{target}"
        rule = "domain-no-sqlalchemy"
        owner = "AIP-011"
        expiry = "2020-01-01"
        reason = "expired on purpose"
        removal_issue = "#077"
        """,
    )
    rc, _, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
        today=date(2026, 8, 4),
    )
    assert rc == 1
    joined = "\n".join(err)
    assert "expired" in joined.lower()
    # The underlying violation is also unwaived because exception is expired.
    assert "domain-no-sqlalchemy" in joined


def test_missing_removal_issue_rejected(arch_mod, tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    expiry = (date.today() + timedelta(days=10)).isoformat()
    _write(
        root / "scripts/quality/arch_exceptions.toml",
        f"""
        [[exceptions]]
        path = "backend/domain/clean/x.py"
        rule = "domain-no-sqlalchemy"
        owner = "AIP-011"
        expiry = "{expiry}"
        reason = "no removal"
        """,
    )
    rc, _, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 1
    assert any("removal_issue" in line or "missing required fields" in line for line in err)


def test_ownerless_exception_rejected(arch_mod, tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    expiry = (date.today() + timedelta(days=10)).isoformat()
    _write(
        root / "scripts/quality/arch_exceptions.toml",
        f"""
        [[exceptions]]
        path = "backend/domain/clean/x.py"
        rule = "domain-no-sqlalchemy"
        owner = "unassigned"
        expiry = "{expiry}"
        reason = "no owner"
        removal_issue = "#077"
        """,
    )
    rc, _, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 1
    assert any("owner" in line.lower() for line in err)


def test_api_orm_import_detected(arch_mod, tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    _write(
        root / "backend/api/v1/route.py",
        """
        from backend.infrastructure.db.models import ResumeModel
        from backend.tasks.resume_tasks import process_resume_pipeline
        """,
    )
    _write(root / "scripts/quality/arch_exceptions.toml", "# empty\n")
    rc, _, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 1
    joined = "\n".join(err)
    assert "api-no-orm-models" in joined
    assert "api-no-tasks" in joined


def test_from_package_import_submodule_orm_detected(arch_mod, tmp_path: Path) -> None:
    """Regression: `from backend.infrastructure.db import models` must fire api-no-orm-models."""
    root = _mini_repo(tmp_path)
    _write(
        root / "backend/api/v1/new_route.py",
        """
        from backend.infrastructure.db import models
        from backend.infrastructure import storage
        from backend.infrastructure.llm import gateway
        """,
    )
    _write(root / "scripts/quality/arch_exceptions.toml", "# empty\n")
    rc, _, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 1
    joined = "\n".join(err)
    assert "api-no-orm-models" in joined
    assert "backend.infrastructure.db.models" in joined
    assert "api-no-storage" in joined
    assert "api-no-llm" in joined


def test_local_from_package_import_submodule_detected(arch_mod, tmp_path: Path) -> None:
    """Nested ImportFrom submodule form (as in jd.py plan-reference helper)."""
    root = _mini_repo(tmp_path)
    _write(
        root / "backend/api/v1/jd_local.py",
        """
        async def _helper():
            from backend.infrastructure.db import models
            return models
        """,
    )
    _write(root / "scripts/quality/arch_exceptions.toml", "# empty\n")
    rc, _, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 1
    joined = "\n".join(err)
    assert "api-no-orm-models" in joined
    assert "jd_local.py" in joined


def test_unknown_rule_in_registry_rejected(arch_mod, tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    expiry = (date.today() + timedelta(days=10)).isoformat()
    _write(
        root / "scripts/quality/arch_exceptions.toml",
        f"""
        [[exceptions]]
        path = "backend/domain/clean/x.py"
        rule = "domain-no-pandas"
        owner = "AIP-011"
        expiry = "{expiry}"
        reason = "unknown rule"
        removal_issue = "#077"
        """,
    )
    rc, _, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 1
    assert any("unknown rule" in line for line in err)


def test_application_provider_sdk_detected(arch_mod, tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    _write(
        root / "backend/application/svc.py",
        """
        import openai
        import anthropic
        """,
    )
    _write(root / "scripts/quality/arch_exceptions.toml", "# empty\n")
    rc, _, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 1
    joined = "\n".join(err)
    assert "application-no-openai" in joined
    assert "application-no-anthropic" in joined


def test_frontend_raw_fetch_without_api_import_fails(arch_mod, tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    _write(
        root / "frontend/src/pages/LeakyPage.tsx",
        """
        export function LeakyPage() {
          fetch('/api/v1/resumes')
          return null
        }
        """,
    )
    _write(root / "scripts/quality/arch_exceptions.toml", "# empty\n")
    rc, _, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 1
    joined = "\n".join(err)
    assert "frontend-page-no-raw-fetch" in joined
    assert "LeakyPage.tsx" in joined


def test_frontend_fetch_with_api_import_passes(arch_mod, tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    _write(
        root / "frontend/src/pages/OkPage.tsx",
        """
        import { listResumes } from '@/api/resume'
        export function OkPage() {
          // feature-specific binary may still call fetch via api module
          fetch('/api/v1/export')
          return listResumes
        }
        """,
    )
    _write(root / "scripts/quality/arch_exceptions.toml", "# empty\n")
    rc, out, err = arch_mod.run_check(
        root=root,
        exceptions_path=root / "scripts/quality/arch_exceptions.toml",
    )
    assert rc == 0, err
    assert any("PASS [architecture]" in line for line in out)


def test_registry_requires_removal_issue_on_real_file() -> None:
    text = ARCH_EXCEPTIONS.read_text(encoding="utf-8")
    assert "removal_issue" in text
    assert "[[exceptions]]" in text
    # Remaining debt entries still point at a concrete removal issue.
    assert any(tag in text for tag in ("#080", "#081", "#082"))


def test_quality_scripts_still_reference_arch_check() -> None:
    # Keep AIP-010 make contract green.
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "scripts/quality/arch_check.py" in makefile
